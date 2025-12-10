"""Database schema models."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Column:
    """Represents a database column."""
    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    comment: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    auto_increment: bool = False
    
    def __str__(self) -> str:
        parts = [f"{self.name}: {self.data_type}"]
        if not self.nullable:
            parts.append("NOT NULL")
        if self.is_primary_key:
            parts.append("PRIMARY KEY")
        if self.auto_increment:
            parts.append("AUTO_INCREMENT")
        if self.default:
            parts.append(f"DEFAULT {self.default}")
        if self.comment:
            parts.append(f"-- {self.comment}")
        return " ".join(parts)


@dataclass
class ForeignKey:
    """Represents a foreign key constraint."""
    column: str
    ref_table: str
    ref_column: str
    constraint_name: Optional[str] = None
    on_delete: str = "NO ACTION"
    on_update: str = "NO ACTION"
    
    def __str__(self) -> str:
        return f"FK: {self.column} -> {self.ref_table}.{self.ref_column}"


@dataclass
class Index:
    """Represents a database index."""
    name: str
    columns: list[str]
    is_unique: bool = False
    index_type: Optional[str] = None
    
    def __str__(self) -> str:
        unique = "UNIQUE " if self.is_unique else ""
        cols = ", ".join(self.columns)
        return f"{unique}INDEX {self.name} ({cols})"


@dataclass
class Table:
    """Represents a database table."""
    name: str
    database: str = "unknown"
    columns: list[Column] = field(default_factory=list)
    primary_keys: list[str] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    indexes: list[Index] = field(default_factory=list)
    engine: str = "InnoDB"
    charset: str = "utf8mb4"
    collation: str = "utf8mb4_unicode_ci"
    comment: Optional[str] = None
    
    def add_column(self, column: Column) -> None:
        """Add a column to the table."""
        self.columns.append(column)
        if column.is_primary_key:
            self.primary_keys.append(column.name)
    
    def add_foreign_key(self, fk: ForeignKey) -> None:
        """Add a foreign key constraint."""
        self.foreign_keys.append(fk)
    
    def add_index(self, index: Index) -> None:
        """Add an index."""
        self.indexes.append(index)
    
    def get_column(self, name: str) -> Optional[Column]:
        """Get a column by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None
    
    def to_markdown(self) -> str:
        """Generate markdown documentation for the table."""
        lines = [
            f"# {self.name.upper()} Table",
            "",
            "## Table Overview",
            f"- **Table Name**: `{self.name}`",
            f"- **Database**: {self.database}",
            f"- **Storage Engine**: {self.engine}",
            f"- **Character Set**: {self.charset}",
            f"- **Collation**: {self.collation}",
        ]
        
        if self.primary_keys:
            lines.append(f"- **Primary Key**: {', '.join(self.primary_keys)}")
        else:
            lines.append("- **Primary Key**: Not defined")
        
        if self.comment:
            lines.append(f"\n**Purpose**: {self.comment}")
        else:
            lines.append("\n**Purpose**: *(Add business purpose here)*")
        
        # Columns section
        lines.extend([
            "",
            "## Columns",
            ""
        ])
        
        for col in self.columns:
            col_info = [f"- **{col.name}**: {col.data_type}"]
            if not col.nullable:
                col_info.append("- NOT NULL")
            if col.default:
                col_info.append(f"- DEFAULT {col.default}")
            if col.comment:
                col_info.append(f"- {col.comment}")
            lines.append(" ".join(col_info))
        
        # Foreign Keys section
        if self.foreign_keys:
            lines.extend([
                "",
                "## Foreign Keys",
                ""
            ])
            for fk in self.foreign_keys:
                lines.append(f"- **{fk.column}** references `{fk.ref_table}.{fk.ref_column}`")
                if fk.on_delete != "NO ACTION":
                    lines.append(f"  - ON DELETE {fk.on_delete}")
                if fk.on_update != "NO ACTION":
                    lines.append(f"  - ON UPDATE {fk.on_update}")
        
        # Indexes section
        if self.indexes:
            lines.extend([
                "",
                "## Indexes",
                ""
            ])
            for idx in self.indexes:
                lines.append(f"- **{idx.name}**: {', '.join(idx.columns)}")
                if idx.is_unique:
                    lines.append("  - UNIQUE")
        
        # Business Rules section
        lines.extend([
            "",
            "## Business Rules",
            "*(Add business logic, validation rules, and constraints here)*",
            "",
            "Examples:",
            "- What values are allowed in status/type fields?",
            "- What are the lifecycle states for this entity?",
            "- Are there any computed or derived fields?",
            "- What are common data patterns (e.g., ID formats)?",
            "",
        ])
        
        return "\n".join(lines)

