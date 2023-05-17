import sqlite3

class LBDB:
    def __init__(self) -> None:
        self.con = sqlite3.connect('loabot.db')
        #self.con.row_factory =  lambda cursor, row: row[0]
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()

    def createTables(self):
 
        try:            
            self.cur.execute("CREATE TABLE user(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
            self.cur.execute("CREATE TABLE chars(user_id INTEGER NOT NULL, char_name STRING PRIMARY KEY, class TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE ON UPDATE NO ACTION)")
            self.cur.execute("CREATE TABLE groups(id INTEGER PRIMARY KEY AUTOINCREMENT, raid_title TEXT NOT NULL, raid TEXT NOT NULL,raid_mode TEXT NOT NULL, raid_mc INTEGER, date TEXT)")
            self.cur.execute("CREATE TABLE raidmember(raid_id INTEGER NOT NULL, user_id INTEGER NOT NULL, char_name TEXT NOT NULL, FOREIGN KEY (raid_id) REFERENCES groups (id), FOREIGN KEY (user_id) REFERENCES user (id), FOREIGN KEY (char_name) REFERENCES chars (char_name))")
            self.cur.execute("CREATE TABLE raids(name TEXT NOT NULL, modes TEXT NOT NULL, member INT NOT NULL, type TEXT NOT NULL)")
            self.con.commit()
        except sqlite3.OperationalError:
            print('tables are already created')
    
    def setup(self):
        self.createTables()
        

    def get_chars(self, user):
        res = self.cur.execute(f'SELECT char_name FROM chars WHERE user_id=(SELECT id FROM user where name="{user}")')
        return res.fetchall()
    
    def get_raids(self):
        res = self.cur.execute('Select * FROM raids')
        return res.fetchall()
        #raiddata={}

        #for n in r:
        #    data = self.cur.execute(f'SELECT modes, member, type FROM raids WHERE name="{n}"')
        #    result = data.fetchall()
        #    print('inner: ', result)

    def add_user(self, user):
        self.cur.execute(f'INSERT INTO user(name) VALUES ("{user}")')
        self.con.commit()
    
    def add_raids(self, name, modes, member, rtype):
        # modes  must be in format '{"modes":["Normal Mode, 1370","...", ...]}'
        self.cur.execute(f'INSERT INTO raids(name, modes, member, type) VALUES (?, ?, ?, ?)', [name, modes, member, rtype])
        self.con.commit()
    
    def add_chars(self, chars, cl, user):
        self.cur.execute(f'INSERT INTO chars(user_id, char_name, class) VALUES((SELECT id FROM user WHERE name="{user}"), "{chars}", "{cl}")')
        self.con.commit()

    def store_raids(self, title, raid, raid_mode, date, mc=None,):
        self.cur.execute(f'INSERT INTO groups(raid_title, raid, raid_mode, raid_mc, date) VALUES(?, ?, ?, ?, ?)', [title, raid, raid_mode, mc, date])
        self.con.commit()


    def show(self, table):
        res = self.cur.execute(f'SELECT * FROM {table}')
        return res.fetchall()
    
    def select_chars(self, username,):
        res = self.cur.execute(f'SELECT char_name FROM chars WHERE user_id=(SELECT id FROM user WHERE name="{username}")').fetchall()
        return res


#db = LBDB()
#db.setup()