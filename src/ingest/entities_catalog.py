"""
Entity Catalog for LightRAG with multiple databases support.
Creates structured metadata entities: Database, Table, Column, Owner, Tag
Supports both MySQL and PostgreSQL databases.
"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from lightrag import LightRAG
from src.core.config import settings
from src.core.logging import logger
from src.models.schema import Table
from src.parsers.sql_parser import MySQLSchemaParser, PostgreSQLSchemaParser


# Database metadata configurations
DATABASE_CONFIGS = {
    "mysql_db": {
        "name": "mysql_application_db",
        "cluster": "production",
        "description": "MySQL production database containing user management and business workflow tables",
        "type": "MySQL",
        "sql_file": "data/vd.sql"
    },
    "postgres_db": {
        "name": "postgres_legacy_db",
        "cluster": "production",
        "description": "PostgreSQL production database containing legacy system data and operational tables",
        "type": "PostgreSQL",
        "sql_file": "data/sqlfile.sql"
    }
}

DEFAULT_OWNER = {
    "name": "Database Team",
    "email": "db-team@company.com"
}

# Common tags for columns
COMMON_TAGS = [
    {"name": "PII", "description": "Personally Identifiable Information - sensitive data requiring protection"},
    {"name": "Authentication", "description": "Authentication and security related fields"},
    {"name": "Timestamp", "description": "Time-based tracking fields"},
    {"name": "Foreign_Key", "description": "Foreign key relationships"},
    {"name": "Primary_Key", "description": "Primary key identifier"},
    {"name": "Required", "description": "NOT NULL fields that must have values"},
]


class EntityCatalogBuilder:
    """Builder for creating entity catalog in LightRAG."""
    
    def __init__(self, rag: LightRAG):
        """
        Initialize entity catalog builder.
        
        Args:
            rag: LightRAG instance
        """
        self.rag = rag
    
    async def create_owner_entity(self) -> None:
        """Create Owner entity."""
        logger.info("Creating Owner entity...")
        
        owner_name = DEFAULT_OWNER["name"]
        
        try:
            await self.rag.acreate_entity(
                entity_name=owner_name,
                entity_data={
                    "description": f"Owner: {owner_name} ({DEFAULT_OWNER['email']})",
                    "entity_type": "owner",
                    "email": DEFAULT_OWNER["email"]
                }
            )
            logger.info(f"✓ Owner: {owner_name}")
        except ValueError as e:
            if "already exists" in str(e):
                logger.info(f"⊙ Owner: {owner_name} (already exists)")
            else:
                raise
    
    async def create_tags(self) -> None:
        """Create common tags for columns."""
        logger.info("Creating Tag entities...")
        
        for tag in COMMON_TAGS:
            try:
                await self.rag.acreate_entity(
                    entity_name=tag["name"],
                    entity_data={
                        "description": tag["description"],
                        "entity_type": "tag"
                    }
                )
                logger.info(f"✓ Tag: {tag['name']}")
            except ValueError as e:
                if "already exists" in str(e):
                    logger.debug(f"⊙ Tag: {tag['name']} (already exists)")
                else:
                    raise
    
    async def create_database_entity(self, db_key: str) -> None:
        """
        Create Database entity.
        
        Args:
            db_key: Database configuration key
        """
        logger.info(f"Creating Database entity for {db_key}...")
        
        config = DATABASE_CONFIGS[db_key]
        entity_name = f"Database:{config['name']}"
        
        try:
            await self.rag.acreate_entity(
                entity_name=entity_name,
                entity_data={
                    "description": f"Database: {config['name']}\nType: {config['type']}\nCluster: {config['cluster']}\nDescription: {config['description']}",
                    "entity_type": "database",
                    "db_type": config["type"],
                    "cluster": config["cluster"],
                    "created_at": datetime.now().isoformat()
                }
            )
            logger.info(f"✓ Database: {config['name']}")
        except ValueError as e:
            if "already exists" in str(e):
                logger.info(f"⊙ Database: {config['name']} (already exists)")
            else:
                raise
    
    async def create_table_entities(self, db_key: str, tables: Dict[str, Table]) -> None:
        """
        Create Table entities with relationships to database.
        
        Args:
            db_key: Database configuration key
            tables: Dictionary of table name to Table object
        """
        logger.info(f"Creating Table entities for {db_key}...")
        
        config = DATABASE_CONFIGS[db_key]
        db_entity_name = f"Database:{config['name']}"
        
        for table_name, table in tables.items():
            table_entity_name = f"Table:{config['name']}.{table_name}"
            
            # Create full description for embedding
            full_description = f"""
Table: {table_name}
Database: {config['name']} ({config['type']})
Engine: {table.engine}
Charset: {table.charset}
Comment: {table.comment or 'N/A'}

Columns:
{self._format_columns(table)}

Foreign Keys:
{self._format_foreign_keys(table)}
"""
            
            # Create table entity (skip if exists)
            try:
                await self.rag.acreate_entity(
                    entity_name=table_entity_name,
                    entity_data={
                        "description": full_description.strip(),
                        "entity_type": "table",
                        "database": config['name'],
                        "engine": table.engine,
                        "row_count": 0,
                        "last_updated": datetime.now().isoformat()
                    }
                )
                logger.info(f"✓ Table: {table_name}")
            except ValueError as e:
                if "already exists" in str(e):
                    logger.debug(f"⊙ Table: {table_name} (already exists)")
                else:
                    raise
            
            # Create Database → Table relationship (skip if exists)
            try:
                await self.rag.acreate_relation(
                    source_entity=db_entity_name,
                    target_entity=table_entity_name,
                    relation_data={
                        "description": f"Database {config['name']} contains table {table_name}",
                        "keywords": "has_table contains database_structure",
                        "weight": 1.5,
                        "relation_type": "HAS_TABLE"
                    }
                )
            except ValueError as e:
                if "already exists" in str(e):
                    logger.debug(f"⊙ Relation: {db_entity_name} → {table_entity_name} (already exists)")
                else:
                    raise
            
            # Create Table → Owner relationship (skip if exists)
            try:
                await self.rag.acreate_relation(
                    source_entity=table_entity_name,
                    target_entity=DEFAULT_OWNER["name"],
                    relation_data={
                        "description": f"Table {table_name} is owned by {DEFAULT_OWNER['name']}",
                        "keywords": "owned_by ownership responsibility",
                        "weight": 1.0,
                        "relation_type": "OWNED_BY"
                    }
                )
            except ValueError as e:
                if "already exists" in str(e):
                    logger.debug(f"⊙ Relation: {table_entity_name} → {DEFAULT_OWNER['name']} (already exists)")
                else:
                    raise
    
    async def create_column_entities(self, db_key: str, tables: Dict[str, Table]) -> int:
        """
        Create Column entities with relationships and tags.
        
        Args:
            db_key: Database configuration key
            tables: Dictionary of table name to Table object
            
        Returns:
            Number of columns created
        """
        logger.info(f"Creating Column entities for {db_key}...")
        
        config = DATABASE_CONFIGS[db_key]
        column_count = 0
        
        for table_name, table in tables.items():
            table_entity_name = f"Table:{config['name']}.{table_name}"
            
            for idx, column in enumerate(table.columns, 1):
                column_entity_name = f"Column:{config['name']}.{table_name}.{column.name}"
                
                # Create column description
                col_description = f"""
Column: {column.name}
Table: {table_name}
Database: {config['name']}
Data Type: {column.data_type}
Nullable: {column.nullable}
Position: {idx}
Primary Key: {column.is_primary_key}
Foreign Key: {column.is_foreign_key}
Default: {column.default or 'None'}
Comment: {column.comment or 'N/A'}
"""
                
                # Create column entity (skip if exists)
                try:
                    await self.rag.acreate_entity(
                        entity_name=column_entity_name,
                        entity_data={
                            "description": col_description.strip(),
                            "entity_type": "column",
                            "table": table_name,
                            "database": config['name'],
                            "dtype": column.data_type,
                            "nullable": column.nullable,
                            "ordinal": idx,
                            "comment": column.comment
                        }
                    )
                except ValueError as e:
                    if "already exists" in str(e):
                        logger.debug(f"⊙ Column: {column_entity_name} (already exists)")
                        continue
                    else:
                        raise
                
                # Create Table → Column relationship (skip if exists)
                try:
                    await self.rag.acreate_relation(
                        source_entity=table_entity_name,
                        target_entity=column_entity_name,
                        relation_data={
                            "description": f"Table {table_name} has column {column.name} at position {idx}",
                            "keywords": "has_column schema_structure column_definition",
                            "weight": 1.0,
                            "relation_type": "HAS_COLUMN",
                            "ordinal": idx
                        }
                    )
                except ValueError as e:
                    if "already exists" in str(e):
                        logger.debug(f"⊙ Relation: {table_entity_name} → {column_entity_name} (already exists)")
                    else:
                        raise
                
                # Create Column → Tag relationships
                tags_to_add = []
                
                if column.is_primary_key:
                    tags_to_add.append("Primary_Key")
                if column.is_foreign_key:
                    tags_to_add.append("Foreign_Key")
                if not column.nullable:
                    tags_to_add.append("Required")
                if "password" in column.name.lower() or "email" in column.name.lower():
                    tags_to_add.append("PII")
                if "time" in column.name.lower() or "date" in column.name.lower():
                    tags_to_add.append("Timestamp")
                if column.name.lower() in ["password", "token", "secret"]:
                    tags_to_add.append("Authentication")
                
                for tag in tags_to_add:
                    try:
                        await self.rag.acreate_relation(
                            source_entity=column_entity_name,
                            target_entity=tag,
                            relation_data={
                                "description": f"Column {column_entity_name} is tagged as {tag}",
                                "keywords": f"tagged classification {tag.lower()}",
                                "weight": 0.8,
                                "relation_type": "TAGGED"
                            }
                        )
                    except ValueError:
                        pass  # Tag relation already exists
                
                column_count += 1
                logger.debug(f"✓ Column: {column.name} ({column.data_type})")
        
        logger.info(f"Created {column_count} column entities")
        return column_count
    
    async def create_foreign_key_relations(self, db_key: str, tables: Dict[str, Table]) -> int:
        """
        Create foreign key relationships between tables.
        
        Args:
            db_key: Database configuration key
            tables: Dictionary of table name to Table object
            
        Returns:
            Number of FK relationships created
        """
        logger.info(f"Creating Foreign Key relationships for {db_key}...")
        
        config = DATABASE_CONFIGS[db_key]
        fk_count = 0
        
        for table_name, table in tables.items():
            for fk in table.foreign_keys:
                # Check if referenced table exists
                if fk.ref_table not in tables:
                    logger.warning(f"Referenced table {fk.ref_table} not found")
                    continue
                
                from_table_entity = f"Table:{config['name']}.{table_name}"
                to_table_entity = f"Table:{config['name']}.{fk.ref_table}"
                
                relation_desc = f"""
Foreign Key Relationship: {table_name} → {fk.ref_table}

Column Mapping:
- {table_name}.{fk.column} references {fk.ref_table}.{fk.ref_column}

Constraint: {fk.constraint_name or 'N/A'}
ON DELETE: {fk.on_delete}
ON UPDATE: {fk.on_update}

Join Pattern:
SELECT * FROM {table_name} 
JOIN {fk.ref_table} ON {table_name}.{fk.column} = {fk.ref_table}.{fk.ref_column}
"""
                
                try:
                    await self.rag.acreate_relation(
                        source_entity=from_table_entity,
                        target_entity=to_table_entity,
                        relation_data={
                            "description": relation_desc.strip(),
                            "keywords": f"foreign_key references {fk.column} {fk.ref_column} join",
                            "weight": 2.0,
                            "relation_type": "REFERENCES",
                            "from_column": fk.column,
                            "to_column": fk.ref_column
                        }
                    )
                    fk_count += 1
                    logger.info(f"✓ FK: {table_name}.{fk.column} → {fk.ref_table}.{fk.ref_column}")
                except ValueError as e:
                    if "already exists" in str(e):
                        logger.debug(f"⊙ FK: {table_name}.{fk.column} → {fk.ref_table}.{fk.ref_column} (already exists)")
                    else:
                        raise
                    if "already exists" in str(e):
                        logger.debug(f"⊙ FK: {table_name} → {fk.ref_table} (already exists)")
                    else:
                        raise
        
        logger.info(f"Created {fk_count} FK relationships")
        return fk_count
    
    def _format_columns(self, table: Table) -> str:
        """Format columns for description."""
        lines = []
        for col in table.columns:
            line = f"- {col.name}: {col.data_type}"
            if not col.nullable:
                line += " NOT NULL"
            if col.is_primary_key:
                line += " PRIMARY KEY"
            if col.comment:
                line += f" -- {col.comment}"
            lines.append(line)
        return "\n".join(lines) if lines else "No columns"
    
    def _format_foreign_keys(self, table: Table) -> str:
        """Format foreign keys for description."""
        lines = []
        for fk in table.foreign_keys:
            lines.append(f"- {fk.column} → {fk.ref_table}.{fk.ref_column}")
        return "\n".join(lines) if lines else "No foreign keys"


async def build_entity_catalog(rag: LightRAG) -> Dict[str, int]:
    """
    Build complete entity catalog for all databases.
    
    Args:
        rag: LightRAG instance
        
    Returns:
        Dictionary with statistics
    """
    logger.info("=" * 80)
    logger.info("Starting Entity Catalog Creation")
    logger.info("=" * 80)
    
    builder = EntityCatalogBuilder(rag)
    stats = {
        "databases": 0,
        "tables": 0,
        "columns": 0,
        "foreign_keys": 0
    }
    
    # Create base entities
    await builder.create_owner_entity()
    await builder.create_tags()
    
    # Process each database
    for db_key, config in DATABASE_CONFIGS.items():
        logger.info(f"\nProcessing database: {config['name']} ({config['type']})")
        
        sql_file = Path(settings.DATA_DIR) / Path(config['sql_file']).name
        
        if not sql_file.exists():
            logger.warning(f"SQL file not found: {sql_file}")
            continue
        
        # Parse schema based on database type
        if config['type'] == 'MySQL':
            parser = MySQLSchemaParser(str(sql_file), config['name'])
        elif config['type'] == 'PostgreSQL':
            parser = PostgreSQLSchemaParser(str(sql_file), config['name'])
        else:
            logger.error(f"Unsupported database type: {config['type']}")
            continue
        
        tables = parser.parse()
        
        # Create database entity
        await builder.create_database_entity(db_key)
        stats["databases"] += 1
        
        # Create table entities
        await builder.create_table_entities(db_key, tables)
        stats["tables"] += len(tables)
        
        # Create column entities
        col_count = await builder.create_column_entities(db_key, tables)
        stats["columns"] += col_count
        
        # Create foreign key relationships
        fk_count = await builder.create_foreign_key_relations(db_key, tables)
        stats["foreign_keys"] += fk_count
    
    logger.info("\n" + "=" * 80)
    logger.info("Entity Catalog Creation Complete!")
    logger.info("=" * 80)
    logger.info(f"Statistics:")
    logger.info(f"  - Databases: {stats['databases']}")
    logger.info(f"  - Tables: {stats['tables']}")
    logger.info(f"  - Columns: {stats['columns']}")
    logger.info(f"  - Foreign Keys: {stats['foreign_keys']}")
    
    return stats

