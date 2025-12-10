"""SQL Schema Parsers for MySQL and PostgreSQL."""

import re
from pathlib import Path
from typing import Dict, Optional

from src.core.logging import logger
from src.models.schema import Table, Column, ForeignKey, Index


class BaseSQLSchemaParser:
    """Base class for SQL schema parsing."""
    
    def __init__(self, sql_file: str, database_name: str = "unknown"):
        """
        Initialize SQL parser.
        
        Args:
            sql_file: Path to SQL dump file
            database_name: Name of the database
        """
        self.sql_file = Path(sql_file)
        self.database_name = database_name
        self.tables: Dict[str, Table] = {}
        
        if not self.sql_file.exists():
            raise FileNotFoundError(f"SQL file not found: {sql_file}")
    
    def parse(self) -> Dict[str, Table]:
        """Parse SQL schema and return tables dictionary."""
        raise NotImplementedError("Subclasses must implement parse()")
    
    def _read_sql_file(self) -> str:
        """Read and return SQL file content."""
        # Try different encodings
        encodings = ['utf-16', 'utf-8', 'latin-1']
        for encoding in encodings:
            try:
                with open(self.sql_file, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                    # Quick check: if we can find common SQL keywords, encoding is likely correct
                    if 'CREATE' in content or 'TABLE' in content:
                        return content
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # Fallback to utf-8 with errors='ignore'
        with open(self.sql_file, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def _clean_sql_comments(self, sql: str) -> str:
        """Remove SQL comments from the content."""
        # Remove single-line comments
        sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
        # Remove multi-line comments
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        return sql


class MySQLSchemaParser(BaseSQLSchemaParser):
    """Parser for MySQL SQL dumps."""
    
    def parse(self) -> Dict[str, Table]:
        """Parse MySQL schema."""
        logger.info(f"Parsing MySQL schema from: {self.sql_file}")
        
        sql_content = self._read_sql_file()
        
        # Extract CREATE TABLE statements
        create_table_pattern = r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*ENGINE\s*=\s*(\w+)(?:\s+DEFAULT\s+CHARSET\s*=\s*(\w+))?(?:\s+COLLATE\s*=\s*([\w_]+))?(?:\s+COMMENT\s*=\s*[\'"]([^\'"]*)[\'"])?'
        
        matches = re.finditer(create_table_pattern, sql_content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            table_name = match.group(1)
            table_def = match.group(2)
            engine = match.group(3) or "InnoDB"
            charset = match.group(4) or "utf8mb4"
            collation = match.group(5) or "utf8mb4_unicode_ci"
            comment = match.group(6)
            
            table = Table(
                name=table_name,
                database=self.database_name,
                engine=engine,
                charset=charset,
                collation=collation,
                comment=comment
            )
            
            # Parse columns and constraints
            self._parse_mysql_table_definition(table, table_def)
            
            self.tables[table_name] = table
            logger.debug(f"Parsed table: {table_name} with {len(table.columns)} columns")
        
        logger.info(f"Found {len(self.tables)} tables in MySQL schema")
        return self.tables
    
    def _parse_mysql_table_definition(self, table: Table, table_def: str):
        """Parse MySQL table definition."""
        # Split into lines
        lines = [line.strip().rstrip(',') for line in table_def.split('\n')]
        
        for line in lines:
            if not line or line.startswith('--'):
                continue
            
            # Check if it's a PRIMARY KEY constraint
            if line.upper().startswith('PRIMARY KEY'):
                pk_match = re.search(r'PRIMARY KEY\s*\((.*?)\)', line, re.IGNORECASE)
                if pk_match:
                    pk_cols = [col.strip('` ') for col in pk_match.group(1).split(',')]
                    table.primary_keys.extend(pk_cols)
                    # Mark columns as primary keys
                    for col in table.columns:
                        if col.name in pk_cols:
                            col.is_primary_key = True
                continue
            
            # Check if it's a FOREIGN KEY constraint
            if line.upper().startswith('CONSTRAINT') or line.upper().startswith('FOREIGN KEY'):
                fk_match = re.search(
                    r'FOREIGN KEY\s*\(`?(\w+)`?\)\s*REFERENCES\s*`?(\w+)`?\s*\(`?(\w+)`?\)(?:\s*ON\s+DELETE\s+(\w+))?(?:\s*ON\s+UPDATE\s+(\w+))?',
                    line,
                    re.IGNORECASE
                )
                if fk_match:
                    fk = ForeignKey(
                        column=fk_match.group(1),
                        ref_table=fk_match.group(2),
                        ref_column=fk_match.group(3),
                        on_delete=fk_match.group(4) or "NO ACTION",
                        on_update=fk_match.group(5) or "NO ACTION"
                    )
                    table.add_foreign_key(fk)
                    # Mark column as foreign key
                    col = table.get_column(fk.column)
                    if col:
                        col.is_foreign_key = True
                continue
            
            # Check if it's a KEY/INDEX
            if line.upper().startswith('KEY') or line.upper().startswith('INDEX') or line.upper().startswith('UNIQUE'):
                is_unique = line.upper().startswith('UNIQUE')
                idx_match = re.search(r'(?:KEY|INDEX)\s+`?(\w+)`?\s*\((.*?)\)', line, re.IGNORECASE)
                if idx_match:
                    idx_name = idx_match.group(1)
                    idx_cols = [col.strip('` ') for col in idx_match.group(2).split(',')]
                    index = Index(name=idx_name, columns=idx_cols, is_unique=is_unique)
                    table.add_index(index)
                continue
            
            # Parse column definition
            col_match = re.match(
                r'`?(\w+)`?\s+(\w+(?:\([\d,]+\))?)\s*(.*)',
                line,
                re.IGNORECASE
            )
            
            if col_match:
                col_name = col_match.group(1)
                data_type = col_match.group(2)
                attributes = col_match.group(3).upper()
                
                column = Column(
                    name=col_name,
                    data_type=data_type,
                    nullable='NOT NULL' not in attributes,
                    is_primary_key='PRIMARY KEY' in attributes,
                    auto_increment='AUTO_INCREMENT' in attributes
                )
                
                # Extract default value
                default_match = re.search(r"DEFAULT\s+([^,\s]+)", attributes)
                if default_match:
                    column.default = default_match.group(1).strip("'\"")
                
                # Extract comment
                comment_match = re.search(r"COMMENT\s+'([^']*)'", attributes)
                if comment_match:
                    column.comment = comment_match.group(1)
                
                table.add_column(column)


class PostgreSQLSchemaParser(BaseSQLSchemaParser):
    """Parser for PostgreSQL SQL dumps."""
    
    def parse(self) -> Dict[str, Table]:
        """Parse PostgreSQL schema."""
        logger.info(f"Parsing PostgreSQL schema from: {self.sql_file}")
        
        sql_content = self._read_sql_file()
        sql_content = self._clean_sql_comments(sql_content)
        
        # Extract CREATE TABLE statements for PostgreSQL
        # Match: CREATE TABLE public.table_name (...) or CREATE TABLE table_name (...)
        # Need to handle nested parentheses in column definitions
        create_table_pattern = r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(?:public\.)?(\w+)\s*\('
        
        # Find all CREATE TABLE statements
        matches = re.finditer(create_table_pattern, sql_content, re.IGNORECASE)
        
        for match in matches:
            table_name = match.group(1)
            start_pos = match.end()
            
            # Find matching closing parenthesis
            # Count parentheses to find the matching one
            depth = 1
            pos = start_pos
            while pos < len(sql_content) and depth > 0:
                if sql_content[pos] == '(':
                    depth += 1
                elif sql_content[pos] == ')':
                    depth -= 1
                pos += 1
            
            if depth == 0:
                # Extract table definition (without outer parentheses)
                table_def = sql_content[start_pos:pos-1]
                
                # Check if there's a semicolon after the closing parenthesis
                remaining = sql_content[pos:].lstrip()
                if not remaining.startswith(';'):
                    continue  # Skip if not properly terminated
                
                table = Table(
                    name=table_name,
                    database=self.database_name,
                    engine="PostgreSQL",
                    charset="UTF8",
                    collation="en_US.UTF-8"
                )
                
                # Parse columns and constraints
                self._parse_postgresql_table_definition(table, table_def)
                
                # Look for table comments
                comment_pattern = rf"COMMENT ON TABLE\s+(?:public\.)?{table_name}\s+IS\s+'([^']*)';"
                comment_match = re.search(comment_pattern, sql_content, re.IGNORECASE)
                if comment_match:
                    table.comment = comment_match.group(1)
                
                self.tables[table_name] = table
                logger.debug(f"Parsed table: {table_name} with {len(table.columns)} columns")
        
        # Parse primary keys (they might be defined separately in ALTER TABLE statements)
        self._parse_postgresql_primary_keys(sql_content)
        
        # Parse foreign keys (they might be defined separately in PostgreSQL)
        self._parse_postgresql_foreign_keys(sql_content)
        
        logger.info(f"Found {len(self.tables)} tables in PostgreSQL schema")
        return self.tables
    
    def _parse_postgresql_table_definition(self, table: Table, table_def: str):
        """Parse PostgreSQL table definition."""
        lines = [line.strip().rstrip(',') for line in table_def.split('\n')]
        
        for line in lines:
            if not line or line.startswith('--'):
                continue
            
            # Check if it's a PRIMARY KEY constraint
            if 'PRIMARY KEY' in line.upper() and not line.strip().split()[0].isalnum():
                pk_match = re.search(r'PRIMARY KEY\s*\((.*?)\)', line, re.IGNORECASE)
                if pk_match:
                    pk_cols = [col.strip('" ') for col in pk_match.group(1).split(',')]
                    table.primary_keys.extend(pk_cols)
                    for col in table.columns:
                        if col.name in pk_cols:
                            col.is_primary_key = True
                continue
            
            # Check if it's a FOREIGN KEY constraint
            if 'FOREIGN KEY' in line.upper():
                fk_match = re.search(
                    r'FOREIGN KEY\s*\(([^)]+)\)\s*REFERENCES\s+(\w+)\s*\(([^)]+)\)',
                    line,
                    re.IGNORECASE
                )
                if fk_match:
                    fk = ForeignKey(
                        column=fk_match.group(1).strip('" '),
                        ref_table=fk_match.group(2),
                        ref_column=fk_match.group(3).strip('" ')
                    )
                    table.add_foreign_key(fk)
                    col = table.get_column(fk.column)
                    if col:
                        col.is_foreign_key = True
                continue
            
            # Parse column definition
            col_match = re.match(
                r'(\w+)\s+(\w+(?:\([\d,]+\))?|character varying\(\d+\)|timestamp(?:\(\d+\))? without time zone)\s*(.*)',
                line,
                re.IGNORECASE
            )
            
            if col_match:
                col_name = col_match.group(1)
                data_type = col_match.group(2)
                attributes = col_match.group(3).upper() if col_match.group(3) else ''
                
                column = Column(
                    name=col_name,
                    data_type=data_type,
                    nullable='NOT NULL' not in attributes,
                    is_primary_key='PRIMARY KEY' in attributes
                )
                
                # Check for DEFAULT
                default_match = re.search(r"DEFAULT\s+([^,]+)", attributes, re.IGNORECASE)
                if default_match:
                    column.default = default_match.group(1).strip("'\"")
                
                # Check for SERIAL/BIGSERIAL (auto-increment in PostgreSQL)
                if 'SERIAL' in data_type.upper() or 'nextval' in attributes.lower():
                    column.auto_increment = True
                
                table.add_column(column)
    
    def _parse_postgresql_primary_keys(self, sql_content: str):
        """Parse ALTER TABLE statements for primary keys."""
        pk_pattern = r'ALTER TABLE\s+(?:ONLY\s+)?(?:public\.)?(\w+)\s+ADD CONSTRAINT\s+\w+_pkey\s+PRIMARY KEY\s*\(([^)]+)\)'
        
        matches = re.finditer(pk_pattern, sql_content, re.IGNORECASE)
        
        for match in matches:
            table_name = match.group(1)
            pk_cols_str = match.group(2)
            
            if table_name in self.tables:
                # Parse column names (can be comma-separated for composite keys)
                pk_cols = [col.strip('" ') for col in pk_cols_str.split(',')]
                self.tables[table_name].primary_keys.extend(pk_cols)
                
                # Mark columns as primary keys
                for col in self.tables[table_name].columns:
                    if col.name in pk_cols:
                        col.is_primary_key = True
    
    def _parse_postgresql_foreign_keys(self, sql_content: str):
        """Parse ALTER TABLE statements for foreign keys."""
        fk_pattern = r'ALTER TABLE\s+(?:ONLY\s+)?(?:public\.)?(\w+)\s+ADD CONSTRAINT\s+(\w+)\s+FOREIGN KEY\s*\(([^)]+)\)\s*REFERENCES\s+(?:public\.)?(\w+)\s*\(([^)]+)\)'
        
        matches = re.finditer(fk_pattern, sql_content, re.IGNORECASE)
        
        for match in matches:
            table_name = match.group(1)
            constraint_name = match.group(2)
            column = match.group(3).strip('" ')
            ref_table = match.group(4)
            ref_column = match.group(5).strip('" ')
            
            if table_name in self.tables:
                fk = ForeignKey(
                    column=column,
                    ref_table=ref_table,
                    ref_column=ref_column,
                    constraint_name=constraint_name
                )
                self.tables[table_name].add_foreign_key(fk)
                
                col = self.tables[table_name].get_column(column)
                if col:
                    col.is_foreign_key = True

