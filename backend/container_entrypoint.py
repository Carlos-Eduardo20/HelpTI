import os
import pwd
import sys
from pathlib import Path


def main():
    if os.geteuid() == 0:
        user = pwd.getpwnam('help-ti')
        database_path = Path(os.getenv(
            'DB_SQLITE_PATH', '/app/instance/helpti.sqlite3'
        )).expanduser()
        if not database_path.is_absolute():
            database_path = Path('/app') / database_path

        database_path.parent.mkdir(parents=True, exist_ok=True)
        os.chown(database_path.parent, user.pw_uid, user.pw_gid)
        if database_path.exists():
            os.chown(database_path, user.pw_uid, user.pw_gid)
        os.initgroups(user.pw_name, user.pw_gid)
        os.setgid(user.pw_gid)
        os.setuid(user.pw_uid)

    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == '__main__':
    main()
