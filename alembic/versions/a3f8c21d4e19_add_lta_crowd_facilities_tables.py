"""add lta crowd density and facilities maintenance tables

Revision ID: a3f8c21d4e19
Revises: 91711aab5efb
Create Date: 2026-04-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f8c21d4e19'
down_revision: Union[str, Sequence[str], None] = '91711aab5efb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend lta_disruptions with new columns
    op.add_column('lta_disruptions', sa.Column('status', sa.String(length=10), nullable=True))
    op.add_column('lta_disruptions', sa.Column('affected_stations', sa.Text(), nullable=True))
    op.add_column('lta_disruptions', sa.Column('free_bus', sa.Text(), nullable=True))
    op.add_column('lta_disruptions', sa.Column('free_shuttle', sa.Text(), nullable=True))
    op.add_column('lta_disruptions', sa.Column('fetched_at', sa.DateTime(), nullable=True))

    # New table: lta_crowd_density
    op.create_table(
        'lta_crowd_density',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('station_code', sa.String(length=10), nullable=False),
        sa.Column('train_line', sa.String(length=10), nullable=False),
        sa.Column('crowd_level', sa.String(length=5), nullable=False),
        sa.Column('source', sa.String(length=10), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_lta_crowd_density_timestamp', 'lta_crowd_density', ['timestamp'])
    op.create_index('ix_lta_crowd_density_station_code', 'lta_crowd_density', ['station_code'])
    op.create_index('ix_lta_crowd_density_train_line', 'lta_crowd_density', ['train_line'])
    op.create_index('ix_lta_crowd_line_station_ts', 'lta_crowd_density', ['train_line', 'station_code', 'timestamp'])

    # New table: lta_facilities_maintenance
    op.create_table(
        'lta_facilities_maintenance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_code', sa.String(length=10), nullable=False),
        sa.Column('station_name', sa.String(length=100), nullable=False),
        sa.Column('train_line', sa.String(length=10), nullable=False),
        sa.Column('equipment_type', sa.String(length=20), nullable=False),
        sa.Column('equipment_id', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_lta_facilities_station_code', 'lta_facilities_maintenance', ['station_code'])
    op.create_index('ix_lta_facilities_fetched_at', 'lta_facilities_maintenance', ['fetched_at'])


def downgrade() -> None:
    op.drop_index('ix_lta_facilities_fetched_at', table_name='lta_facilities_maintenance')
    op.drop_index('ix_lta_facilities_station_code', table_name='lta_facilities_maintenance')
    op.drop_table('lta_facilities_maintenance')

    op.drop_index('ix_lta_crowd_line_station_ts', table_name='lta_crowd_density')
    op.drop_index('ix_lta_crowd_density_train_line', table_name='lta_crowd_density')
    op.drop_index('ix_lta_crowd_density_station_code', table_name='lta_crowd_density')
    op.drop_index('ix_lta_crowd_density_timestamp', table_name='lta_crowd_density')
    op.drop_table('lta_crowd_density')

    op.drop_column('lta_disruptions', 'fetched_at')
    op.drop_column('lta_disruptions', 'free_shuttle')
    op.drop_column('lta_disruptions', 'free_bus')
    op.drop_column('lta_disruptions', 'affected_stations')
    op.drop_column('lta_disruptions', 'status')
