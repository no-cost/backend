# Data Export

- **Date**: {{ lookup('pipe', 'date --iso-8601=seconds') }}
- **Site tag**: {{ tenant_tag }}
- **Application**: {{ service_type }}

> **Disclaimer**: These instructions are provided as a general developer guide and may
> not reflect the latest version of {{ service_type }}. We are not responsible
> for any issues arising from the import process. Always refer to the official
> {{ service_type }} documentation for up-to-date instructions.
>
> Please note that we cannot assist you with migrating the content to a new platform,
> that's something you (or your dev team) need to do!

## Archive contents

- `files/app/public/` — user-generated content (uploads, assets, etc.); it does not contain the entire application source code!
- `database.sql` — full MariaDB database dump
{% if service_type == 'flarum' %}

## Importing into Flarum

1. Install Flarum following the [official guide](https://docs.flarum.org/install).
2. Import the database dump into your Flarum database:

   ```bash
   mysql -u <user> -p <dbname> < database.sql
   ```

3. Copy `files/app/public/assets/` into your Flarum `public/assets/` directory (avatars, extension assets, etc.).
4. Update `config.php` with your database credentials and set `url` to your new domain (don't forget to update your DNS).
5. Clear the cache and run migrations:

   ```bash
   php flarum cache:clear
   php flarum migrate
   ```

{% elif service_type == 'mediawiki' %}

## Importing into MediaWiki

1. Install MediaWiki following the [official guide](https://www.mediawiki.org/wiki/Manual:Installation_guide).
2. Import the database dump into your MediaWiki database:

   ```bash
   mysql -u <user> -p <dbname> < database.sql
   ```

3. Copy `files/app/public/images/` into your MediaWiki `images/` directory (uploaded files and their thumbnails).
4. Update `LocalSettings.php` with your database credentials and set `$wgServer` to your new domain (don't forget to update your DNS).
5. Run the database update script to reconcile any schema differences:

   ```bash
   php maintenance/run.php update --quick
   ```

{% elif service_type == 'wordpress' %}

## Importing into WordPress

1. Install WordPress following the [official guide](https://developer.wordpress.org/advanced-administration/before-install/howto-install/).
2. Import the database dump into your WordPress database:

   ```bash
   mysql -u <user> -p <dbname> < database.sql
   ```

3. Copy `files/app/public/wp-content/uploads/` into your WordPress `wp-content/uploads/` directory.
4. Update `wp-config.php` with your database credentials. Set `WP_HOME` and `WP_SITEURL` to your new domain (don't forget to update your DNS).
5. WordPress stores URLs in the database (including in serialized data). Use WP-CLI to rewrite them:

   ```bash
   wp search-replace 'https://old-domain.com' 'https://new-domain.com' --all-tables --precise
   ```

6. Flush cache:

   ```bash
   wp cache flush
   wp rewrite flush
   ```

{% endif %}

We are sad to see you go, but hope you find a new home for your content. Good luck!
