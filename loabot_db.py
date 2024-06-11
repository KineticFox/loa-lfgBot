import logging
import mariadb
import mariadb.constants.CLIENT as CLIENT
import os
import dotenv

logger = logging.getLogger('DB')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formater = logging.Formatter('%(asctime)s - %(levelname)s %(name)s:%(msg)s', '%y-%m-%d, %H:%M') 
handler.setFormatter(formater)
logger.addHandler(handler)
logger.propagate = False


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
          char_name varchar(70) NOT NULL,
          emoji varchar(50) NOT NULL
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


        CREATE TABLE {messages} (
          m_id text NOT NULL,
          c_id varchar(30) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        CREATE TABLE {raidmember} (
          raid_id int NOT NULL,
          user_id int NOT NULL,
          char_name varchar(70) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;


        CREATE TABLE {user} (
          id int NOT NULL,
          name varchar(100) NOT NULL,
          user_id bigint NOT NULL
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
                self.cur.execute(f'SELECT count(table_name) FROM information_schema.tables WHERE table_type = "base table" AND table_schema="{name}" AND table_name LIKE ?;', [sql])
                res = self.cur.fetchone()
                counter = res['count(table_name)']
                if counter == 0:
                    self.createTables(guild)
                    


        except mariadb.Error as e:
            logger.warning(f'DB setup Error - {e}')

    def use_db(self):
        """
        specifies which table should be used.\n
        Is set via env variable
        """
        name = os.getenv("DB_NAME")
        self.cur.execute(f"use {name};")
    
    def close(self):
        """
        closes DB conection
        """
        self.connection.close()

    def get_my_raids(self, user_id, table) -> 'list[dict]':
        """
        DB Helperfunction for raids of a player

        Returns: 
        --------
            char_name (str): char name,
            raid (str): raid,
            raid_title (str): title of the group,
            date(str): list of raid dates,
            dc_id (str): thread id of the group
        """

        try:
            self.cur.execute(f'SELECT {table}_raidmember.char_name, {table}_groups.raid, {table}_groups.raid_title, {table}_groups.dc_id, {table}_groups.date FROM {table}_raidmember INNER JOIN {table}_groups ON {table}_raidmember.raid_id={table}_groups.id AND {table}_raidmember.user_id=(SELECT id FROM {table}_user WHERE user_id=?)', [user_id])
            res = self.cur.fetchall()
            return res            
        
        except mariadb.Error as e:
            logger.warning(f'DB get my raids Error - {e}')
        

    def get_chars(self, user_id, table) -> 'list[dict]':
        """
        DB Helperfunction for chars of a player

        Returns:
        -------- 
            char_name (str): char name,
            class (str): class of the char,
            ilvl (int): ilvl of the char
            emoji (str): emoji discord string
        """
        try:
            self.cur.execute(f'SELECT char_name, class, ilvl, emoji FROM {table}_chars WHERE user_id=(SELECT id FROM {table}_user where user_id=?)', [user_id]) 
            res = self.cur.fetchall()
            return res
        except mariadb.Error as e:
            logger.warning(f'Database get chars Error - {e}')
            return ['error']
        
    def get_char_ilvl(self, name, table) -> dict:
        """
        DB Helperfunction for one ilvl of a specified char name

        Returns:
        -------- 
            ilvl (int): ilvl of given char
        """
        try:
            self.cur.execute(f'SELECT ilvl FROM {table}_chars WHERE char_name=?', [name])
            res = self.cur.fetchone()
            return res
        except mariadb.Error as e:
            logger.warning(f'DB get ilvl Error - {e}')

    def get_group(self, id, table)-> dict:
        """
        DB Helperfunction for retrieving all values of one group identified by its id

        Returns:
        --------
            dict (dict) { 
                id (int): group db id,
                raid_title (str): title of the group,
                raid (str): which raid,
                raid_mode (str): mode of the raid (normal hard, etc.),
                raid_mc (int): current member in this group,
                date (str): planned date of the group,
                dc_id (str): thread id of this group
            }
        """
        try:
            self.cur.execute(f'SELECT * FROM {table}_groups WHERE id=?', [id])
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'Database get group Error - {e}')

    def get_raidtype(self, name, table) -> dict:
        """
        DB Helperfunction for retrieving max member count and type from a raid

        Returns:
        --------
            dict (dict) { 
                member (int): max member count for this raid,
                type (str): type of the raid (Legion, etc.)
            }
        """
        try:
            self.cur.execute(f'SELECT member,type FROM {table}_raids WHERE name=?', [name]) 
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'Database raid type Error - {e}')
    
    def get_raidmember(self, group_id, table) -> dict:
        """
        DB Helperfunction for retrieving the first entry user from a specified group

        Returns:
        --------
            dict (dict) { 
                user_id (int): db user id of this user,
            }
        """
        try:
            self.cur.execute(f'SELECT user_id FROM {table}_raidmember WHERE raid_id=?',[group_id])
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'DB raidmember Error - {e}')

    def get_username(self, id, table) ->dict:
        """
        DB Helperfunction for retrieving the dc user name

        Parameters:
        -----------
            id (int): the id of the user,
            table (string): refers on which DC-Server this command is invoked

        Returns:
        --------
            dict (dict) { 
                name (str): the dc user name
            }
        """
        try:
            self.cur.execute(f'SELECT name FROM {table}_user WHERE id=?',[id])
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'DB user name Error - {e}')

    def update_group_mc(self, id, count, table):
        """
        Updates the member count of specified Group.

        Parameters:
        -----------
            id (int): the id of the group u want to update,
            count (int): the new member count,
            table (string): refers on which DC-Server this command is invoked

        Returns:
        --------
            None
        """
        try:
            self.cur.execute(f'UPDATE {table}_groups SET raid_mc=? WHERE id=?', [count, id]) 
        except mariadb.Error as e:
            logger.warning(f'DB update mc Error - {e}')
    
    def raidmember_check(self, raidid, user_id, table):
        """
        Gets the charname of a user from a give group. If user is in this group returns dict with users charname, else empty dict.

        Parameters:
        -----------
            raid_id (int): the id of the group
            user_id (string): the dc user id
            table (string): refers on which DC-Server this command is invoked

        Returns:
        --------
            dict (dict) {
                char_name (string): the charname
            }
        """
        try:
            self.cur.execute(f'SELECT char_name FROM {table}_raidmember WHERE raid_id=? AND user_id=(SELECT id FROM {table}_user WHERE user_id=?)', [raidid, user_id])
            return self.cur.fetchone()
        except mariadb.Error as e:
            logger.warning(f'raidmember check Error: {e}')

    def add_groupmember(self, raid_id, user_id, charname, table)->None:
        """
        Adds a user and his char to the raidmember table with the group he joined.

        Parameters:
        -----------
            raid_id (int): the id of the group
            user_id (string): the dc user id
            charname (string): the name of the character
            table (string): refers on which DC-Server this command is invoked

        Returns:
        --------
            None
        """
        try:
            self.cur.execute(f'INSERT INTO {table}_raidmember(raid_id, user_id, char_name) Values(?, (SELECT id FROM {table}_user WHERE user_id=?), ?)', [raid_id, user_id, charname])
        except mariadb.Error as e:
           logger.warning(f'Database add groupmember Error - {e}')

    def remove_groupmember(self, user_id, raidid, table) -> None:
        """
        Removes a user from the raidmember table.

        Parameters:
        -----------
            raidid (int): the id of the group
            user_id (string): the dc user id
            table (string): refers on which DC-Server this command is invoked

        Returns:
        --------
            None
        """
        try:
            self.cur.execute(f'DELETE FROM {table}_raidmember WHERE raid_id=? AND user_id=(SELECT id FROM {table}_user WHERE user_id=?)', [raidid, user_id]) 
        except mariadb.Error as e:
            logger.warning(f'Database remove Groupmember Error: {e}')

    def update_chars(self, charname, ilvl, delete, table, user)-> str:
        """
        updates a given char in the DB, deletes the char if delete=yes

        Parameters:
        -----------
            charname (string): the name of the char
            ilvl (int): the ilvl of the char
            delete (boolean): boolean to determin if char should be deleted or not
            table (string): refers on which DC-Server this command is invoked
            user (int): the user id of the discord user

        Returns:
        --------
            string: feedback for this action
        """
        try:
            self.cur.execute(f'SELECT user_id FROM {table}_chars WHERE char_name=?', [charname])
            res = self.cur.fetchone()
            if res is None :
                return 'This Char does not exist / Dieser Char existiert nicht'
            else:
                self.cur.execute(f'SELECT id FROM {table}_user WHERE user_id=?', [user])
                user_res = self.cur.fetchone()
                if res['user_id'] == user_res['id']:
                    if delete == 'no':
                        self.cur.execute(f'SELECT user_id FROM {table}_chars WHERE char_name=?', [charname])
                        res = self.cur.fetchone()
                        if res is None :
                            return 'This Char does not exist / Dieser Char existiert nicht'
                        else:
                            self.cur.execute(f'UPDATE {table}_chars SET ilvl=? WHERE char_name=?', [ilvl, charname])
                            return 'Updated char'
                    elif delete == 'yes':
                        self.cur.execute(f'SELECT raid_id FROM {table}_raidmember WHERE char_name=?', [charname])
                        res = self.cur.fetchall()
                        if len(res) == 0 or res is None:
                            self.cur.execute(f'DELETE FROM {table}_chars WHERE char_name=? AND ilvl=?', [charname, ilvl])
                            return 'deleted char'
                        else:
                            return 'Your Char is member of some raids, please leave first / Dein Char ist noch Mitglied von Raids bitte verlasse diese zuerst.'
                else:
                    return 'You are naughty, this is not your Char / Du bist ungezogen, das ist nicht dein Char'
        except mariadb.Error as e:
            logger.warning(f'Databse update char Error - {e}')
            return f'Databse update char Error - {e}'
            
    def get_raids(self, table)->'list[dict]':
        """
        Returns a list with all Raids available

        Parameters:
        -----------
            table (string): refers on which DC-Server this command is invoked

        Returns:
        --------
            [
                {
                    name (string): name of the Raid
                    mode (string): Raidmode
                    member (int): Max membercount of the raid
                    type (string): Raidtype
                }
            ]
        """
        try:
            self.cur.execute(f'Select * FROM {table}_raids')
            return self.cur.fetchall()
        except mariadb.Error as e:
            logger.warning(f'Database get raid Error - {e}')
            return ['error']
    
    def get_typed_raids_inorder(self, table, type):
        """
        returns raids of chosen Type ordered by release
        """
        try:
            self.cur.execute(f'SELECT * FROM {table}_raids WHERE type=? ORDER BY raid_order ASC', [type])
            return self.cur.fetchall()
        except mariadb.Error as e:
            logger.warning(f'Database get raid Error - {e}')

        
    def get_raid_mc(self, raid) -> dict:
        """
        Returns the max membercount for specified raid

        Parameters:
        -----------

            raid (string): raid name

        Returns:
        --------
            dict (dict){
                member (int): max member count for raid
            }
        """
        table = 'TechKeller'
        try:
            self.cur.execute(f'SELECT member FROM {table}_raids WHERE name=?', [raid])
            res = self.cur.fetchone()
            return res
        except mariadb.Error as e:
            logger.warning(f'Database get raid mc Error - {e}')


    def get_raids_setup(self,tables)-> 'list[dict]':
        """
        x

        Parameters:
        -----------

            table (string): refers on which DC-Server this command is invoked

        Returns:
        --------
            [
                {
                    name (string): name of the Raid
                    mode (string): Raidmode
                    member (int): Max membercount of the raid
                    type (string): Raidtype
                }
            ]
        """
        try:
            for table in tables:
                self.cur.execute(f'Select * FROM {table}_raids')
                return self.cur.fetchall()
        except mariadb.Error as e:
            logger.warning(f'Database get raid Error - {e}')
            return ['error']

    def save_image(self, raid, url, table):
        """
        Saves the image url with the raid name

        Parameters:
        -----------
            raid (string): name of the raid
            url (string): url of the image
            table (string): refers on which DC-Server this command is invoked

        Returns:
        --------
            None
        """
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
        """ 
        x

        Parameters:
        -----------

            table (string): refers on which DC-Server this command is invoked

        Returns:
        --------
            None
        """
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

    def add_user(self, user, user_id, table):
        try:
            self.cur.execute(f'SELECT name FROM {table}_user WHERE user_id=?', [user_id])
            res = self.cur.fetchall()
            if len(res) != 0:
                logger.info(f'User {user} already exists in DB')
                return f'User {user} already exists in DB'
            else:
                self.cur.execute(f'INSERT INTO {table}_user(name, user_id) VALUES (?,?)', [user, user_id])
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
                self.cur.execute(f'UPDATE {table}_raids SET modes=?, member=?, type=? WHERE name=?', [modes, member, rtype, name])
                return 0

        except mariadb.Error as e:
            logger.warning(f'Add raid insertion error: {e}')


    
    def add_chars(self, chars, cl, user, ilvl, role, table, user_id, emoji):
        try:
            self.cur.execute(f'SELECT id FROM {table}_user WHERE user_id=?', [user_id])
            user_check = self.cur.fetchone()
            if user_check is None or len(user_check) == 0:
                self.add_user(user, user_id, table)
                self.cur.execute(f'INSERT INTO {table}_chars(user_id, char_name, class, ilvl, role, emoji) VALUES((SELECT id FROM {table}_user WHERE user_id=?), ?, ?, ?, ?, ?)', [user_id, chars, cl, ilvl, role, emoji]) 
                return f'Added your char {chars} to the DB'
            else:                
                self.cur.execute(f'SELECT char_name FROM {table}_chars WHERE char_name=?', [chars]) 
                res = self.cur.fetchall()
                if len(res) != 0:
                    logger.info(f'Char {chars} already exists in DB')
                    return f'Char {chars} already exists in DB'
                else:
                    self.cur.execute(f'INSERT INTO {table}_chars(user_id, char_name, class, ilvl, role, emoji) VALUES((SELECT id FROM {table}_user WHERE user_id=?), ?, ?, ?, ?,?)', [user_id, chars, cl, ilvl, role, emoji]) 
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
        
        
    
    def select_chars(self, user_id, table):
        try:
            self.cur.execute(f'SELECT char_name, emoji FROM {table}_chars WHERE user_id=(SELECT id FROM {table}_user WHERE user_id=?)', [user_id])
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
        
    def all_user(self, table):
        try:
            self.cur.execute(f'SELECT name FROM {table}_user')
            res = self.cur.fetchall()
            return res
        except mariadb.Error as e:
            logger.warning(f'all user DB error - {e}')

    def all_chars(self, table):
        try:
            self.cur.execute(f'SELECT char_name, class FROM {table}_chars')
            res = self.cur.fetchall()
            return res
        except mariadb.Error as e:
            logger.warning(f'all chars DB error - {e}')

    def update_user(self, table, name, u_id):
        try:
            self.cur.execute(f'UPDATE {table}_user SET user_id=? WHERE name=?', [u_id, name])
            #res = self.cur.fetchall()
        except mariadb.Error as e:
            logger.warning(f'update user DB error - {e}')
    
    def update_emoji(self, table, name, emoji):
        try:
            self.cur.execute(f'UPDATE {table}_chars SET emoji=? WHERE char_name=?', [emoji, name])
            #res = self.cur.fetchall()
        except mariadb.Error as e:
            logger.warning(f'update emoji DB error - {e}')

    def get_group_overview(self, table:str)->list:
        """
        returns a list of groups  
        """#which aren't at max membercount and are not Guardian raids
        
        try:
            self.cur.execute(f'SELECT {table}_groups.raid_title, {table}_groups.raid, {table}_groups.raid_mode, {table}_groups.dc_id, {table}_groups.raid_mc FROM {table}_groups WHERE {table}_groups.raid_mc < (SELECT TechKeller_raids.member FROM TechKeller_raids WHERE {table}_groups.raid=TechKeller_raids.name) ') #AND (SELECT TechKeller_raids.type FROM TechKeller_raids WHERE TechKeller_raids.name={table}_groups.raid) != "Guardian"
            res = self.cur.fetchall()
            return res
        except mariadb.Error as e:
            logger.warning(f'group overview DB error - {e}')
    
    def add_admin(self, user_id:str)->str:
        """
        Adds user_id to the Discord Admins table.
        """
        try:
            self.cur.execute(f'SELECT id FROM Techkeller_admins WHERE user_id=?', [user_id])
            res = self.cur.fetchall()
            if len(res) != 0:
                logger.info(f'User already exists in DB')
                return f'User already exists in DB'
            else:
                self.cur.execute(f'INSERT INTO Techkeller_admins(user_id) VALUES (?)', [user_id])
                return f'added your DC-User to the DB'
        except mariadb.Error as e:
            logger.warning(f'Add user admin insert error: {e}')

    def update_date(self, table:str, group_id:int, date:str) -> None:
        """
        Updates the date and time of given group

        Parameters:
        ----------
            table (string): refers on which DC-Server this command is invoked
            group_id (int): the id of the group which should be updated
            date (string): the new date and time

        Returns:
        --------
            None
        """

        try:
            self.cur.execute(f'UPDATE {table}_groups SET date=? WHERE id=?', [date, group_id])
        except mariadb.Error as e:
            logger.warning(f'Date update error on group {group_id}')

    def get_all_char_classes(self) -> 'list[dict]':
        """
        gets all Charakter classes in the DB

        Returns:
        --------
            list[dict]
        """

        try:
            self.cur.execute(f'SELECT * FROM lostArk_char_class')
            res = self.cur.fetchall()
            return res
        except mariadb.Error as e:
            logger.warning(f'Get all classes error - {e}')

    def get_all_chars(self, charclass: str) -> 'list[dict]':
        """
            Gets all Chars belonging to selected Char Class.

            Parameters:
            -----------
                charclass (string): The Characterclass name
            
            Returns:
            --------
                list[dicts]: the resulting Chars with emojis

        """

        try:
            self.cur.execute(f'SELECT * FROM lostArk_chars WHERE char_class=(SELECT id FROM lostArk_char_class WHERE class_name=?)', [charclass])
            res = self.cur.fetchall()
            return res
        except mariadb.Error as e:
            logger.warning(f'Get all classes error - {e}')

    def get_char_data(self, char: str) -> 'list[dict]':
        """
            Gets Charname and Char emoji from spcified Charclass

            Parameters:
            -----------
                char (string): The char you want to get the emoji for

            Returns:
            --------
                dict: The dict with the char emoji

        """

        try:
            self.cur.execute(f'SELECT * FROM lostArk_chars WHERE char_name=?', [char])
            res = self.cur.fetchone()
            return res
        
        except mariadb.Error as e:
            logger.warning(f'Get char emoji error - {e}')
