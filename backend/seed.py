from getpass import getpass
from sqlalchemy import select
from .database import SessionLocal
from .models import Role, User
from .config import get_settings
from .auth.security import hash_password

ROLES=['Administrator','Purple Team Engineer','SOC Analyst','Detection Engineer','Viewer']

def main():
    s=get_settings()
    if s.admin_password in ('CHANGE_ME_BEFORE_SEEDING','CHANGE_ME') or len(s.admin_password)<12:
        raise SystemExit('Set ADMIN_PASSWORD in .env to a strong password (12+ chars) before seeding.')
    with SessionLocal() as db:
        for name in ROLES:
            if not db.scalar(select(Role).where(Role.name==name)):
                db.add(Role(name=name))
        db.commit()
        role=db.scalar(select(Role).where(Role.name=='Administrator'))
        if not db.scalar(select(User).where(User.email==s.admin_email.lower())):
            db.add(User(email=s.admin_email.lower(),role_id=role.id,password_hash=hash_password(s.admin_password)))
            db.commit()
            print('Admin account created:',s.admin_email)
        else:
            print('Admin already exists; password unchanged')

if __name__=='__main__':main()
