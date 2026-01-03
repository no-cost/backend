from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Site(Base):
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
    hostname: Mapped[str] = mapped_column(String(length=255), nullable=True)
    installed_at: Mapped[datetime] = mapped_column(nullable=True, default=datetime.now)

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
    """Donations are per site, in EUR"""

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
