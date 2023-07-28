import sqlite3
import logging
from collections import namedtuple

logger = logging.getLogger('DB')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formater = logging.Formatter('%(name)s:%(levelname)s: %(msg)s')
handler.setFormatter(formater)
logger.addHandler(handler)
logger.propagate = False

class LBDB:
    def __init__(self) -> None:
        self.con = sqlite3.connect('loabot.db')
        #self.con.row_factory =  lambda cursor, row: row[0]
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        
    
    def createTables(self):
 
        try:            
            self.cur.execute("CREATE TABLE user(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
            self.cur.execute("CREATE TABLE chars(user_id INTEGER NOT NULL, char_name STRING PRIMARY KEY, class TEXT NOT NULL, ilvl INTEGER NOT NULL, FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE ON UPDATE NO ACTION)")
            self.cur.execute("CREATE TABLE groups(id INTEGER PRIMARY KEY AUTOINCREMENT, raid_title TEXT NOT NULL, raid TEXT NOT NULL,raid_mode TEXT NOT NULL, raid_mc INTEGER, date TEXT)")
            self.cur.execute("CREATE TABLE raidmember(raid_id INTEGER NOT NULL, user_id INTEGER NOT NULL, char_name TEXT NOT NULL, FOREIGN KEY (raid_id) REFERENCES groups (id) ON DELETE CASCADE, FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE, FOREIGN KEY (char_name) REFERENCES chars (char_name))")
            self.cur.execute("CREATE TABLE raids(name TEXT NOT NULL, modes TEXT NOT NULL, member INT NOT NULL, type TEXT NOT NULL)")
            self.cur.execute("CREATE TABLE messages(m_id INT NOT NULL, c_id INT NOT NULL)")
            self.con.commit()
            logger.info('Created all tables')
        except sqlite3.OperationalError:
            logger.info('already created')

    
    def setup(self):
        self.createTables()
        

    def get_chars(self, user):
        try:
            res = self.cur.execute(f'SELECT char_name, class, ilvl FROM chars WHERE user_id=(SELECT id FROM user where name="{user}")')
            return res.fetchall()
        except sqlite3.Error as e:
            logger.warning(f'Database Error - {e}')
            return ['error']

    def get_group(self, id):
        try:
            res = self.cur.execute(f'SELECT raid_mc FROM groups WHERE id={id}')
            return res.fetchone()
        except sqlite3.Error as e:
            logger.warning(f'Database Error - {e}')

    def update_group_mc(self, id, count):
        try:
            self.cur.execute(f'UPDATE groups SET raid_mc={count} WHERE id={id}')
        except sqlite3.Error as e:
            logger.warning(f'DB Error - {e}')

        

    
    def get_raids(self):
        try:
            res = self.cur.execute('Select * FROM raids')
            return res.fetchall()
        except sqlite3.Error as e:
            logger.warning(f'Database Error - {e}')
            return ['error']
        #raiddata={}

        #for n in r:
        #    data = self.cur.execute(f'SELECT modes, member, type FROM raids WHERE name="{n}"')
        #    result = data.fetchall()
        #    print('inner: ', result)
    def get_messages(self):
        try:
            res = self.cur.execute('Select * FROM messages')
            return res.fetchall()
        except sqlite3.Error as e:
            logger.warning(f'Database Error - {e}')
            return ['error']

    def add_user(self, user):
        try:
            row = self.cur.execute(f'SELECT name FROM user WHERE name="{user}"')
            res = row.fetchall()
            if len(res) != 0:
                logger.info(f'User {user} already exists in DB')
                return f'User {user} already exists in DB'
            else:
                self.cur.execute(f'INSERT INTO user(name) VALUES ("{user}")')
                self.con.commit()
                return f'added your DC-User "{user}" to the DB'
        except sqlite3.Error as e:
            logger.warning(f'Add user insert error: {e}')
    
    def add_message(self, m_id, c_id):
        try:
            self.cur.execute(f'INSERT INTO messages(m_id, c_id) VALUES (?, ?)', [m_id, c_id])
            self.con.commit()
        except sqlite3.Error as e:
            logger.warning(f'Add messages insert error: {e}')
    
        
    
    def add_raids(self, name, modes, member, rtype):
        # modes  must be in format '{"modes":["Normal Mode, 1370","...", ...]}'
        try:
            self.cur.execute(f'INSERT INTO raids(name, modes, member, type) VALUES (?, ?, ?, ?)', [name, modes, member, rtype])
            self.con.commit()
        except sqlite3.Error as e:
            logger.warning(f'Add user insertion error: {e}')
    
    def add_chars(self, chars, cl, user, ilvl):
        try:
            row = self.cur.execute(f'SELECT char_name FROM chars WHERE char_name="{chars}"')
            res = row.fetchall()
            if len(res) != 0:
                logger.info(f'Char {chars} already exists in DB')
                return f'Char {chars} already exists in DB'
            else:
                self.cur.execute(f'INSERT INTO chars(user_id, char_name, class, ilvl) VALUES((SELECT id FROM user WHERE name="{user}"), "{chars}", "{cl}","{ilvl}")')
                self.con.commit()
                return f'Add your char {chars} to the DB'
        except sqlite3.Error as e:
            logger.warning(f'Add user insertion error: {e}')
            return f'add char DB error: {e}'

    def store_raids(self, title, raid, raid_mode, date, mc=None,):
        
        try:
            self.cur.execute(f'INSERT INTO groups(raid_title, raid, raid_mode, raid_mc, date) VALUES(?, ?, ?, ?, ?)', [title, raid, raid_mode, mc, date])
            self.con.commit()
            return self.cur.lastrowid
        except sqlite3.Error as e:
            logger.warning(f'Store raid insertion error: {e}')
    
    def delete_raids(self, id):
        try:
            self.cur.execute(f'DELETE FROM groups WHERE id={id}')
            self.con.commit()
        except sqlite3.Error as e:
            logger.warning(f'Delete Raid error: {e}')


    def show(self, table):
        try:
            res = self.cur.execute(f'SELECT * FROM {table}')
            logger.info(res)
            return res.fetchall()
            
        except sqlite3.Error as e:
            logger.warning(f'Show table Error: {e}')
            return {}
        
        
    
    def select_chars(self, username,):
        try:
            res = self.cur.execute(f'SELECT char_name FROM chars WHERE user_id=(SELECT id FROM user WHERE name="{username}")').fetchall()
            return res
        except sqlite3.Error as e:
            logger.warning(f'Show table Error: {e}')
            return ['DB error']
        
    def raw_SQL(self, command):
        try:
            self.cur.execute(command)
            self.con.commit()
            return "command worked"
        except sqlite3.Error as e:
            return f'command failed; {e}'
            logger.warning(f'Raw SQL Error: {e}')
