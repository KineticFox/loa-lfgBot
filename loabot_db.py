import logging
import mariadb
import os
import dotenv

logger = logging.getLogger('DB')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formater = logging.Formatter('%(name)s:%(levelname)s: %(msg)s')
handler.setFormatter(formater)
logger.addHandler(handler)
logger.propagate = False

#meine server id: 777872580870668308 --> guild id?!

dotenv.load_dotenv()

class LBDB:
    def __init__(self) -> None:
        #self.con = sqlite3.connect('data/loabot.db')
        #self.con.row_factory =  lambda cursor, row: row[0]
        #self.con.row_factory = sqlite3.Row
        #self.cur = self.con.cursor()
        self.connection = mariadb.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PW"),
            host=os.getenv("DB_IP"),
            port=int(os.getenv("DB_PORT")),
            #database=os.getenv("DB_NAME")
        )
        self.connection.autocommit = True
        self.cur = self.connection.cursor(dictionary=True)
        
    """
    def createTables(self):
 
        try:            
            self.cur.execute("CREATE TABLE user(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
            self.cur.execute("CREATE TABLE chars(user_id INTEGER NOT NULL, char_name STRING PRIMARY KEY, class TEXT NOT NULL, ilvl INTEGER NOT NULL, role TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE ON UPDATE NO ACTION)")
            self.cur.execute("CREATE TABLE groups(id INTEGER PRIMARY KEY AUTOINCREMENT, raid_title TEXT NOT NULL, raid TEXT NOT NULL,raid_mode TEXT NOT NULL, raid_mc INTEGER, date TEXT, dc_id INTEGER)")
            self.cur.execute("CREATE TABLE raidmember(raid_id INTEGER NOT NULL, user_id INTEGER NOT NULL, char_name TEXT NOT NULL, FOREIGN KEY (raid_id) REFERENCES groups (id) ON DELETE CASCADE, FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE, FOREIGN KEY (char_name) REFERENCES chars (char_name))")
            self.cur.execute("CREATE TABLE raids(name TEXT NOT NULL, modes TEXT NOT NULL, member INT NOT NULL, type TEXT NOT NULL)")
            self.cur.execute("CREATE TABLE messages(m_id INT NOT NULL, c_id INT NOT NULL)")
            self.cur.execute("CREATE TABLE images(raid TEXT NOT NULL, url TEXT NOT NULL)")
            self.con.commit()
            logger.info('Created all tables')
        except sqlite3.OperationalError:
            logger.info('already created')
    """

    
    def setup(self):
        #self.createTables()
        try:
            name = os.getenv("DB_NAME")
            self.cur.execute(f"use {name};")
            logger.info("DB connection established")

        except mariadb.Error as e:
            logger.warning(f'DB setup Error - {e}')
    
    def close(self):
        logger.info('Closing DB connection')
        self.connection.close()
        

    def get_chars(self, user):
        try:
            self.cur.execute(f'SELECT char_name, class, ilvl FROM chars WHERE user_id=(SELECT id FROM user where name=?)', [user]) #"{user}"
            res = self.cur.fetchall()
            return res
        except mariadb.Error as e:
            logger.warning(f'Database get chars Error - {e}')
            return ['error']
        
    def get_char_ilvl(self, name):
        try:
            self.cur.execute('SELECT ilvl FROM chars WHERE char_name=?', [name])
            res = self.cur.fetchone()
            return res
        except mariadb.Error as e:
            logger.warning(f'DB get ilvl Error - {e}')

    def get_group(self, id):
        try:
            self.cur.execute(f'SELECT * FROM groups WHERE id=?', [id]) #{id}
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'Database get group Error - {e}')

    def get_raidtype(self, name):
        try:
            self.cur.execute(f'SELECT member,type FROM raids WHERE name=?', [name]) #"{name}"
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'Database raid type Error - {e}')

    def update_group_mc(self, id, count):
        try:
            self.cur.execute(f'UPDATE groups SET raid_mc=? WHERE id=?', [count, id]) #{count} {id}
        except mariadb.Error as e:
            logger.warning(f'DB update mc Error - {e}')
    
    def raidmember_check(self, raidid, username):
        try:
            self.cur.execute(f'SELECT char_name FROM raidmember WHERE raid_id=? AND user_id=(SELECT id FROM user WHERE name=?)', [raidid, username]) #"{raidid}" "{username}"
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'raidmember check Error: {e}')

    def add_groupmember(self, raid_id, user_name, charname):
        try:
            self.cur.execute(f'INSERT INTO raidmember(raid_id, user_id, char_name) Values(?, (SELECT id FROM user WHERE name=?), ?)', [raid_id, user_name, charname]) #"{raid_id}" "{user_name}" "{charname}"
            #(SELECT id FROM user WHERE name="{user}")
        except mariadb.Error as e:
           logger.warning(f'Database add groupmember Error - {e}')

    def remove_groupmember(self, name, raidid):
        try:
            self.cur.execute(f'DELETE FROM raidmember WHERE raid_id=? AND user_id=(SELECT id FROM user WHERE name=?)', [raidid, name]) #{raidid} "{name}"
        except mariadb.Error as e:
            logger.warning(f'Database remove Groupmember Error: {e}')

    def update_chars(self, charname, ilvl, delete:None):
        try:
            if delete == 'no':
                self.cur.execute(f'UPDATE chars SET ilvl=? WHERE char_name=?', [ilvl, charname]) #{ilvl} "{charname}"
                return 'Updated char'
            elif delete == 'yes':
                self.cur.execute(f'DELETE FROM chars WHERE char_name=? AND ilvl=?', [charname, ilvl])
                return 'deleted char'
        except mariadb.Error as e:
            logger.warning(f'Databse update char Error - {e}')
            return f'Databse update char Error - {e}'
            
    def get_raids(self):
        try:
            self.cur.execute('Select * FROM raids')
            return self.cur.fetchall()
        except mariadb.Error as e:
            logger.warning(f'Database get raid Error - {e}')
            return ['error']
        #raiddata={}

        #for n in r:
        #    data = self.cur.execute(f'SELECT modes, member, type FROM raids WHERE name="{n}"')
        #    result = data.fetchall()
        #    print('inner: ', result)


    def save_image(self, raid, url):
        try:
            self.cur.execute(f'SELECT * FROM images WHERE raid=?', [raid])
            result = self.cur.fetchone()

            if result is None:
                self.cur.execute(f'INSERT INTO images(raid, url) VALUES(?, ?)', [raid, url]) 
            else:
                logger.debug(f'Images for {raid} already exists')
            
        except mariadb.Error as e:
            logger.warning(f'Database save image Error - {e}')

    def get_image_url(self, raid):
        try:
            self.cur.execute(f'SELECT url FROM images WHERE raid=?', [raid])
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'Database get image Error: {e}')
            


    def get_message(self, raid_id):
        try:
            self.cur.execute(f'Select * FROM messages WHERE c_id=?', [raid_id])
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'Database get message Error - {e}')
            return ['error']

    def add_user(self, user):
        try:
            self.cur.execute(f'SELECT name FROM user WHERE name=?', [user])
            res = self.cur.fetchall()
            if len(res) != 0:
                logger.info(f'User {user} already exists in DB')
                return f'User {user} already exists in DB'
            else:
                self.cur.execute(f'INSERT INTO user(name) VALUES (?)', [user])
                return f'added your DC-User "{user}" to the DB'
        except mariadb.Error as e:
            logger.warning(f'Add user insert error: {e}')
    
    def add_message(self, m_id, c_id):
        try:
            self.cur.execute(f'INSERT INTO messages(m_id, c_id) VALUES (?, ?)', [m_id, c_id])
        except mariadb.Error as e:
            logger.warning(f'Add messages insert error: {e}')
    
        
    
    def add_raids(self, name, modes, member, rtype):
        # modes  must be in format '{"modes":["Normal Mode, 1370","...", ...]}'
        try:
            self.cur.execute(f'SELECT * FROM raids WHERE name=?', [name])
            result = self.cur.fetchone()
            if result is None:
                self.cur.execute(f'INSERT INTO raids(name, modes, member, type) VALUES (?, ?, ?, ?)', [name, modes, member, rtype])
                return 1
            else:
                logger.debug(f'Raid {name} already exists, updating instead')
                self.cur.execute(f'UPDATE raids SET modes=?, member=?, type=? WHERE name=? (name, modes, member, type) VALUES (?, ?, ?, ?)', [modes, member, rtype, name])
                return 0

        except mariadb.Error as e:
            logger.warning(f'Add raid insertion error: {e}')


    
    def add_chars(self, chars, cl, user, ilvl, role):
        try:
            self.cur.execute('SELECT id FROM user WHERE name=?', [user])
            user_check = self.cur.fetchone()
            if user_check is None or len(user_check) == 0:
                self.add_user(user)
                self.cur.execute(f'INSERT INTO chars(user_id, char_name, class, ilvl, role) VALUES((SELECT id FROM user WHERE name=?), ?, ?, ?, ?)', [user, chars, cl, ilvl, role]) #"{user}" "{chars}" "{cl}" "{ilvl}" "{role}"
                return f'Added your char {chars} to the DB'
            else:                
                self.cur.execute(f'SELECT char_name FROM chars WHERE char_name=?', [chars]) #"{chars}"
                res = self.cur.fetchall()
                if len(res) != 0:
                    logger.info(f'Char {chars} already exists in DB')
                    return f'Char {chars} already exists in DB'
                else:
                    self.cur.execute(f'INSERT INTO chars(user_id, char_name, class, ilvl, role) VALUES((SELECT id FROM user WHERE name=?), ?, ?, ?, ?)', [user, chars, cl, ilvl, role]) #"{user}" "{chars}" "{cl}" "{ilvl}" "{role}"
                    return f'Added your char {chars} to the DB'
        except mariadb.Error as e:
            logger.warning(f'Add user insertion error: {e}')
            return f'Please register your user first'

    def store_group(self, title, raid, raid_mode, date, dc_id, mc=0):

        try:
            self.cur.execute(f'INSERT INTO groups(raid_title, raid, raid_mode, raid_mc, date, dc_id) VALUES(?, ?, ?, ?, ?, ?)', [title, raid, raid_mode, mc, date, dc_id])
            self.cur.execute('SELECT id FROM groups WHERE dc_id=?', [dc_id])
            res = self.cur.fetchone()
            return res[0]
        except mariadb.Error as e:
            logger.warning(f'Store group insertion error: {e}')
    
    def delete_raids(self, id):
        try:
            self.cur.execute(f'DELETE FROM groups WHERE id=?', [id]) #{id}
            self.cur.execute(f'DELETE FROM raidmember WHERE raid_id=?', [id]) #{id}
            self.con.commit()
        except mariadb.Error as e:
            logger.warning(f'Delete Raid error: {e}')


    def show(self, table):
        try:
            self.cur.execute(f'SELECT * FROM {table}')
            res = self.cur.fetchall()            
            logger.info(res)
            return res
            
        except mariadb.Error as e:
            logger.warning(f'Show table Error: {e}')
            return {}
        
        
    
    def select_chars(self, username):
        try:
            self.cur.execute(f'SELECT char_name FROM chars WHERE user_id=(SELECT id FROM user WHERE name=?)', [username])
            res = self.cur.fetchall()
            return res
        except mariadb.Error as e:
            logger.warning(f'Select chars table Error: {e}')
            return ['DB error']
    
    def get_charRole(self, charname):
        try:
            self.cur.execute(f'SELECT role FROM chars WHERE char_name=?', [charname])
            res = self.cur.fetchone() 
            return res
        except mariadb.Error as e:
            logger.warning(f'get char role Error: {e}')
        
    def raw_SQL(self, command):
        try:
            self.cur.execute(command)
            return "command worked"
        except mariadb.Error as e:
            logger.warning(f'Raw SQL Error: {e}')
            return f'command failed; {e}'
            
