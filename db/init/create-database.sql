/* =====================================================================================
   Tienda+ · inicialización de UNA base de datos de microservicio (entorno local)
   Se ejecuta una vez por cada contenedor de SQL Server (catalog-db y orders-db).
   - Crea la base de datos $(DB_NAME).
   - Crea un login/usuario $(DB_USER) con permisos SOLO sobre esa base de datos
     (mínimo privilegio): lectura/escritura de datos + DDL para que la app cree sus tablas.
   - Idempotente: se puede ejecutar en cada "docker compose up" sin efectos secundarios.
   Las variables $(...) las inyecta sqlcmd desde el contenedor *-db-init (compose.yaml).
   ===================================================================================== */
SET NOCOUNT ON;
GO

IF DB_ID(N'$(DB_NAME)') IS NULL
    CREATE DATABASE [$(DB_NAME)];
GO

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'$(DB_USER)')
    CREATE LOGIN [$(DB_USER)] WITH PASSWORD = N'$(DB_PASSWORD)', DEFAULT_DATABASE = [$(DB_NAME)];
ELSE
    ALTER LOGIN [$(DB_USER)] WITH PASSWORD = N'$(DB_PASSWORD)';
GO

USE [$(DB_NAME)];
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'$(DB_USER)')
    CREATE USER [$(DB_USER)] FOR LOGIN [$(DB_USER)];
ALTER ROLE db_datareader ADD MEMBER [$(DB_USER)];
ALTER ROLE db_datawriter ADD MEMBER [$(DB_USER)];
ALTER ROLE db_ddladmin  ADD MEMBER [$(DB_USER)];
GO

PRINT N'Base de datos $(DB_NAME) lista para $(DB_USER).';
GO
