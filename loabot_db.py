import logging
import mariadb
import mariadb.constants.CLIENT as CLIENT
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
            client_flag=CLIENT.MULTI_STATEMENTS
            #database=os.getenv("DB_NAME")
        )
        self.connection.autocommit = True
        self.cur = self.connection.cursor(dictionary=True)
        
    
    def createTables(self, guild):
 

        chars = f'{guild}_chars'
        groups = f'{guild}_groups' 
        images = f'{guild}_images'
        messages = f'{guild}_messages'
        raidmember = f'{guild}_raidmember'
        raids = f'{guild}_raids'
        user = f'{guild}_user'
         
        query = f"""
        CREATE TABLE {chars} (
          user_id int NOT NULL,
          class varchar(50) NOT NULL,
          ilvl int NOT NULL,
          role varchar(20) NOT NULL,
          char_name varchar(70) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        CREATE TABLE {groups} (
          id int NOT NULL,
          raid_title varchar(70) NOT NULL,
          raid varchar(50) NOT NULL,
          raid_mode varchar(50) NOT NULL,
          raid_mc int DEFAULT NULL,
          date varchar(40) DEFAULT NULL,
          dc_id text DEFAULT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        CREATE TABLE {images} (
          raid varchar(40) NOT NULL,
          url varchar(300) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        CREATE TABLE {messages} (
          m_id text NOT NULL,
          c_id varchar(30) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        CREATE TABLE {raidmember} (
          raid_id int NOT NULL,
          user_id int NOT NULL,
          char_name varchar(70) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;


        CREATE TABLE {raids} (
          name varchar(50) NOT NULL,
          modes varchar(150) NOT NULL,
          member int NOT NULL,
          type varchar(50) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;


        CREATE TABLE {user} (
          id int NOT NULL,
          name varchar(100) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        ALTER TABLE {chars}
          ADD PRIMARY KEY (char_name),
          ADD KEY user_id (user_id);


        ALTER TABLE {groups}
          ADD PRIMARY KEY (id);


        ALTER TABLE {raidmember}
          ADD KEY raid_id (raid_id),
          ADD KEY user_id (user_id),
          ADD KEY char_name (char_name);


        ALTER TABLE {user}
          ADD PRIMARY KEY (id);

        ALTER TABLE {groups}
          MODIFY id int NOT NULL AUTO_INCREMENT;

        ALTER TABLE {user}
          MODIFY id int NOT NULL AUTO_INCREMENT;

        ALTER TABLE {chars}
          ADD CONSTRAINT chars_ibfk_1 FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE ON UPDATE NO ACTION;

        ALTER TABLE {raidmember}
          ADD CONSTRAINT raidmember_ibfk_1 FOREIGN KEY (raid_id) REFERENCES groups (id),
          ADD CONSTRAINT raidmember_ibfk_2 FOREIGN KEY (user_id) REFERENCES user (id),
          ADD CONSTRAINT raidmember_ibfk_3 FOREIGN KEY (char_name) REFERENCES chars (char_name);
        """

        try:
            self.cur.execute(query)
            logger.info(f'Table creation for {guild} complete')

        except mariadb.Error as e:
            logger.warning(f'DB setup error - {e}')


    
    def setup(self, table_names):
        #self.createTables()
        try:
            name = os.getenv("DB_NAME")
            self.cur.execute(f"use {name};")
            logger.info("DB connection established")
            logger.info("testing if Tables exist")
            for guild in table_names:
                sql = guild + '%' 
                self.cur.execute(f'SELECT count(table_name) FROM information_schema.tables WHERE table_type = "base table" AND table_schema="testing" AND table_name LIKE ?;', [sql])
                res = self.cur.fetchone()
                counter = res['count(table_name)']

                if counter == 0:
                    self.createTables(guild)
                    


        except mariadb.Error as e:
            logger.warning(f'DB setup Error - {e}')
    
    def close(self):
        logger.info('Closing DB connection')
        self.connection.close()
        

    def get_chars(self, user, table):
        try:
            self.cur.execute(f'SELECT char_name, class, ilvl FROM {table}_chars WHERE user_id=(SELECT id FROM user where name=?)', [user]) #"{user}"
            res = self.cur.fetchall()
            return res
        except mariadb.Error as e:
            logger.warning(f'Database get chars Error - {e}')
            return ['error']
        
    def get_char_ilvl(self, name, table):
        try:
            self.cur.execute(f'SELECT ilvl FROM {table}_chars WHERE char_name=?', [name])
            res = self.cur.fetchone()
            return res
        except mariadb.Error as e:
            logger.warning(f'DB get ilvl Error - {e}')

    def get_group(self, id, table):
        try:
            self.cur.execute(f'SELECT * FROM {table}_groups WHERE id=?', [id])
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'Database get group Error - {e}')

    def get_raidtype(self, name, table):
        try:
            self.cur.execute(f'SELECT member,type FROM {table}_raids WHERE name=?', [name]) 
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'Database raid type Error - {e}')

    def update_group_mc(self, id, count, table):
        try:
            self.cur.execute(f'UPDATE {table}_groups SET raid_mc=? WHERE id=?', [count, id]) 
        except mariadb.Error as e:
            logger.warning(f'DB update mc Error - {e}')
    
    def raidmember_check(self, raidid, username, table):
        try:
            self.cur.execute(f'SELECT char_name FROM {table}_raidmember WHERE raid_id=? AND user_id=(SELECT id FROM {table}_user WHERE name=?)', [raidid, username])
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'raidmember check Error: {e}')

    def add_groupmember(self, raid_id, user_name, charname, table):
        try:
            self.cur.execute(f'INSERT INTO {table}_raidmember(raid_id, user_id, char_name) Values(?, (SELECT id FROM {table}_user WHERE name=?), ?)', [raid_id, user_name, charname])
        except mariadb.Error as e:
           logger.warning(f'Database add groupmember Error - {e}')

    def remove_groupmember(self, name, raidid, table):
        try:
            self.cur.execute(f'DELETE FROM {table}_raidmember WHERE raid_id=? AND user_id=(SELECT id FROM {table}_user WHERE name=?)', [raidid, name]) 
        except mariadb.Error as e:
            logger.warning(f'Database remove Groupmember Error: {e}')

    def update_chars(self, charname, ilvl, table, delete:None):
        try:
            if delete == 'no':
                self.cur.execute(f'UPDATE {table}_chars SET ilvl=? WHERE char_name=?', [ilvl, charname])
                return 'Updated char'
            elif delete == 'yes':
                self.cur.execute(f'DELETE FROM {table}_chars WHERE char_name=? AND ilvl=?', [charname, ilvl])
                return 'deleted char'
        except mariadb.Error as e:
            logger.warning(f'Databse update char Error - {e}')
            return f'Databse update char Error - {e}'
            
    def get_raids(self, table):
        try:
            self.cur.execute(f'Select * FROM {table}_raids')
            return self.cur.fetchall()
        except mariadb.Error as e:
            logger.warning(f'Database get raid Error - {e}')
            return ['error']
        
    def get_raids_setup(self,tables):
        try:
            for table in tables:
                self.cur.execute(f'Select * FROM {table}_raids')
                return self.cur.fetchall()
        except mariadb.Error as e:
            logger.warning(f'Database get raid Error - {e}')
            return ['error']

    def save_image(self, raid, url, table):
        try:
            self.cur.execute(f'SELECT * FROM {table}_images WHERE raid=?', [raid])
            result = self.cur.fetchone()

            if result is None:
                self.cur.execute(f'INSERT INTO {table}_images(raid, url) VALUES(?, ?)', [raid, url]) 
            else:
                logger.debug(f'Images for {raid} already exists')
            
        except mariadb.Error as e:
            logger.warning(f'Database save image Error - {e}')

    def get_image_url(self, raid, table):
        try:
            self.cur.execute(f'SELECT url FROM {table}_images WHERE raid=?', [raid])
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'Database get image Error: {e}')
            


    def get_message(self, raid_id, table):
        try:
            self.cur.execute(f'Select * FROM {table}_messages WHERE c_id=?', [raid_id])
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'Database get message Error - {e}')
            return ['error']

    def add_user(self, user, table):
        try:
            self.cur.execute(f'SELECT name FROM {table}_user WHERE name=?', [user])
            res = self.cur.fetchall()
            if len(res) != 0:
                logger.info(f'User {user} already exists in DB')
                return f'User {user} already exists in DB'
            else:
                self.cur.execute(f'INSERT INTO {table}_user(name) VALUES (?)', [user])
                return f'added your DC-User "{user}" to the DB'
        except mariadb.Error as e:
            logger.warning(f'Add user insert error: {e}')
    
    def add_message(self, m_id, c_id, table):
        try:
            self.cur.execute(f'INSERT INTO {table}_messages(m_id, c_id) VALUES (?, ?)', [m_id, c_id])
        except mariadb.Error as e:
            logger.warning(f'Add messages insert error: {e}')
    
        
    
    def add_raids(self, name, modes, member, rtype, table):
        # modes  must be in format '{"modes":["Normal Mode, 1370","...", ...]}'
        try:
            self.cur.execute(f'SELECT * FROM {table}_raids WHERE name=?', [name])
            result = self.cur.fetchone()
            if result is None:
                self.cur.execute(f'INSERT INTO {table}_raids(name, modes, member, type) VALUES (?, ?, ?, ?)', [name, modes, member, rtype])
                return 1
            else:
                logger.debug(f'Raid {name} already exists, updating instead')
                self.cur.execute(f'UPDATE {table}_raids SET modes=?, member=?, type=? WHERE name=? (name, modes, member, type) VALUES (?, ?, ?, ?)', [modes, member, rtype, name])
                return 0

        except mariadb.Error as e:
            logger.warning(f'Add raid insertion error: {e}')


    
    def add_chars(self, chars, cl, user, ilvl, role, table):
        try:
            self.cur.execute(f'SELECT id FROM {table}_user WHERE name=?', [user])
            user_check = self.cur.fetchone()
            if user_check is None or len(user_check) == 0:
                self.add_user(user, table)
                self.cur.execute(f'INSERT INTO {table}_chars(user_id, char_name, class, ilvl, role) VALUES((SELECT id FROM {table}_user WHERE name=?), ?, ?, ?, ?)', [user, chars, cl, ilvl, role]) #"{user}" "{chars}" "{cl}" "{ilvl}" "{role}"
                return f'Added your char {chars} to the DB'
            else:                
                self.cur.execute(f'SELECT char_name FROM {table}_chars WHERE char_name=?', [chars]) #"{chars}"
                res = self.cur.fetchall()
                if len(res) != 0:
                    logger.info(f'Char {chars} already exists in DB')
                    return f'Char {chars} already exists in DB'
                else:
                    self.cur.execute(f'INSERT INTO {table}_chars(user_id, char_name, class, ilvl, role) VALUES((SELECT id FROM {table}_user WHERE name=?), ?, ?, ?, ?)', [user, chars, cl, ilvl, role]) #"{user}" "{chars}" "{cl}" "{ilvl}" "{role}"
                    return f'Added your char {chars} to the DB'
        except mariadb.Error as e:
            logger.warning(f'Add user insertion error: {e}')
            return f'Please register your user first'

    def store_group(self, title, raid, raid_mode, date, dc_id, table ,mc=0):

        try:
            self.cur.execute(f'INSERT INTO {table}_groups(raid_title, raid, raid_mode, raid_mc, date, dc_id) VALUES(?, ?, ?, ?, ?, ?)', [title, raid, raid_mode, mc, date, dc_id])
            self.cur.execute('SELECT LAST_INSERT_ID()')
            res = self.cur.fetchone()
            return res
        except mariadb.Error as e:
            logger.warning(f'Store group insertion error: {e}')
    
    def delete_raids(self, id, table):
        try:
            self.cur.execute(f'DELETE FROM {table}_raidmember WHERE raid_id=?', [id])
            self.cur.execute(f'DELETE FROM {table}_groups WHERE id=?', [id])
        except mariadb.Error as e:
            logger.warning(f'Delete Raid error: {e}')


    def show(self, table, tablename):
        try:
            self.cur.execute(f'SELECT * FROM {table}_{tablename}')
            res = self.cur.fetchall()            
            logger.info(res)
            return res
            
        except mariadb.Error as e:
            logger.warning(f'Show table Error: {e}')
            return {}
        
        
    
    def select_chars(self, username, table):
        try:
            self.cur.execute(f'SELECT char_name FROM {table}_chars WHERE user_id=(SELECT id FROM {table}_user WHERE name=?)', [username])
            res = self.cur.fetchall()
            return res
        except mariadb.Error as e:
            logger.warning(f'Select chars table Error: {e}')
            return ['DB error']
    
    def get_charRole(self, charname, table):
        try:
            self.cur.execute(f'SELECT role FROM {table}_chars WHERE char_name=?', [charname])
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
            
