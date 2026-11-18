"""Create the physical product catalog.

Revision ID: c7e4a91f2b35
Revises: 9b5b0c3d4e6f
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c7e4a91f2b35"
down_revision: Union[str, Sequence[str], None] = "9b5b0c3d4e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(20), server_default=sa.text("'PHYSICAL'"), nullable=False),
        sa.Column("category", sa.String(30), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(), nullable=False),
        sa.Column("ingredients", sa.Text(), nullable=True),
        sa.Column("benefits", sa.Text(), nullable=True),
        sa.Column("properties", sa.Text(), nullable=True),
        sa.Column("suggested_use", sa.Text(), nullable=True),
        sa.Column("warnings", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind IN ('PHYSICAL', 'COURSE')", name="ck_products_kind"),
        sa.CheckConstraint(
            "(kind = 'PHYSICAL' AND category IN "
            "('HERBAL_MEDICINE', 'MEDICINAL_PLANT', 'SUPPLEMENT', 'HEALTHY_SNACK')) "
            "OR (kind = 'COURSE' AND category IS NULL)",
            name="ck_products_kind_category",
        ),
        sa.CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_public", "products", ["kind", "is_active", "created_at"])
    op.create_table(
        "product_images",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_product_images_position"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "position", name="uq_product_images_position"),
    )


def downgrade() -> None:
    op.drop_table("product_images")
    op.drop_index("ix_products_public", table_name="products")
    op.drop_table("products")
