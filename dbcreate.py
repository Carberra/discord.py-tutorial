from sqlite3 import connect

Database = connect("database.db", check_same_thread=False)
Cursor = Database.cursor()

commands = (
	"CREATE TABLE users (UserID integer PRIMARY KEY, XP integer DEFAULT 0, Level integer DEFAULT 0, Strikes integer DEFAULT 0, XPLockedUntil text DEFAULT CURRENT_TIMESTAMP, MutedUntil text DEFAULT CURRENT_TIMESTAMP)",
	"CREATE TABLE system (Key text PRIMARY KEY, Value text)",
	"INSERT INTO system (Key) VALUES ('version')",
)

for command in commands:
	Cursor.execute(command)

Database.commit()
Database.close()
quit()