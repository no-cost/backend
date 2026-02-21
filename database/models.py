from __future__ import annotations

import typing as t
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, func, or_, select
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
        String(length=72),
        nullable=False,  # bcrypt
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
    donated_amount: Mapped[float] = mapped_column(default=0.0, server_default="0")
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
        return (self.donated_amount or 0) > 0.0

    def has_donor_perks(self) -> bool:
        """Returns whether the site admin has donated enough to have perks (such as the footer removed)"""
        return (self.donated_amount or 0) >= 7.0

    # clsmethods
    @classmethod
    async def get_all_active(
        cls, db: AsyncSession, *additional_filters, match_removed: bool = False
    ):
        """Get all sites as an async iterator."""

        filters = [*additional_filters]
        if not match_removed:
            filters.insert(0, cls.removed_at.is_(None))

        result = await db.stream(select(cls).where(*filters))
        async for row in result.scalars():
            yield row

    @classmethod
    async def get_by_hostname(
        cls, db: AsyncSession, hostname: str, *additional_filters
    ) -> Site | None:
        """Get a site by its hostname."""

        result = await db.execute(
            select(cls).where(cls.hostname == hostname, *additional_filters)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_tag_or_hostname(
        cls, db: AsyncSession, value: str, *, match_removed: bool = False
    ) -> Site | None:
        """Get a single site by tag or hostname (used during login, as same e-mail can have multiple sites)."""

        filters = [or_(cls.tag == value, cls.hostname == value)]
        if not match_removed:
            filters.insert(0, cls.removed_at.is_(None))

        result = await db.execute(select(cls).where(*filters))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_identifier(
        cls, db: AsyncSession, identifier: str, *, match_removed: bool = False
    ) -> Site | None:
        """Get a single site matching by tag, email, or hostname."""

        filters = [cls._identifier_filter(identifier)]
        if not match_removed:
            filters.insert(0, cls.removed_at.is_(None))

        result = await db.execute(select(cls).where(*filters))
        return result.scalar_one_or_none()

    @classmethod
    async def get_all_by_identifier(
        cls, db: AsyncSession, identifier: str, *, match_removed: bool = False
    ):
        """Get all sites matching by tag, email, or hostname as an async iterator."""

        filters = [cls._identifier_filter(identifier)]
        if not match_removed:
            filters.insert(0, cls.removed_at.is_(None))

        result = await db.stream(select(cls).where(*filters))
        async for row in result.scalars():
            yield row

    @classmethod
    def _identifier_filter(cls, identifier: str):
        return or_(
            cls.tag == identifier,
            cls.admin_email == identifier,
            cls.hostname == identifier,
        )


class SiteStats(Base):
    """Historical resource usage snapshot for a tenant site."""

    __tablename__ = "site_stats"
    __table_args__ = (Index("ix_site_stats_tag_collected", "site_tag", "collected_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_tag: Mapped[str] = mapped_column(
        String(length=32), ForeignKey("sites.tag"), nullable=False
    )
    content_count: Mapped[int] = mapped_column(default=0)
    user_count: Mapped[int] = mapped_column(default=0)
    assets_mb: Mapped[float] = mapped_column(default=0.0)
    collected_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.current_timestamp()
    )
