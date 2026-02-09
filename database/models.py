from __future__ import annotations

import typing as t
from datetime import datetime

from sqlalchemy import String, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

if t.TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Base(DeclarativeBase):
    pass


class Site(Base):
    """A model for a tenant. Each account = site."""

    __tablename__ = "sites"

    tag: Mapped[str] = mapped_column(
        String(length=32),
        primary_key=True,
        unique=True,
        nullable=False,
    )

    # account
    admin_email: Mapped[str] = mapped_column(String(length=255), nullable=False)
    admin_password: Mapped[str] = mapped_column(
        String(length=72), nullable=False  # bcrypt
    )

    # config
    site_type: Mapped[str] = mapped_column(String(length=30), nullable=False)
    hostname: Mapped[str] = mapped_column(String(length=255), nullable=False)
    installed_at: Mapped[datetime] = mapped_column(nullable=True)

    # removal
    removal_reason: Mapped[str] = mapped_column(String(length=255), nullable=True)
    removed_at: Mapped[datetime] = mapped_column(nullable=True)
    removed_ip: Mapped[str] = mapped_column(String(length=45), nullable=True)

    # IPs
    created_ip: Mapped[str] = mapped_column(String(length=45), nullable=True)
    last_login_ip: Mapped[str] = mapped_column(String(length=45), nullable=True)
    last_login_at: Mapped[datetime] = mapped_column(nullable=True)

    # misc
    donated_amount: Mapped[float] = mapped_column(nullable=True)
    """Donations are per site/account, in EUR"""

    # timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )

    def is_installed(self) -> bool:
        """Returns whether the site was installed successfully"""
        return self.installed_at is not None

    def get_parent_domain(self) -> str:
        """Returns the parent domain of the site's hostname"""
        last_2_parts = self.hostname.split(".")[-2:]
        return ".".join(last_2_parts)

    def is_donor(self) -> bool:
        """Returns whether the site admin has donated"""
        return self.donated_amount is not None and self.donated_amount > 0.0

    def has_perks(self) -> bool:
        """Returns whether the site admin has donated enough to have perks (such as the footer removed)"""
        return self.donated_amount is not None and self.donated_amount >= 7.0

    # clsmethods
    @classmethod
    async def get_all_active(cls, db: AsyncSession, *additional_filters):
        """Get all active sites as an async iterator."""

        result = await db.stream(select(cls).where(cls.removed_at.is_(None), *additional_filters))
        async for row in result.scalars():
            yield row

    @classmethod
    async def get_by_hostname(cls, db: AsyncSession, hostname: str, *additional_filters) -> Site | None:
        """Get a site by its hostname."""

        result = await db.execute(select(cls).where(cls.hostname == hostname, *additional_filters))
        return result.scalar_one_or_none()
