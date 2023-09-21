import mariadb

try:
    connection = mariadb.connect(
        user="db_admin",
        password="z4McE9vscBEW3~E7ew",
        host="10.155.20.3",
        port=3307,
        database="testing"
    )
    connection.autocommit = True


except mariadb.Error as e:
    print(e);

cursor = connection.cursor(dictionary=True)

try:
    #cursor.execute("use testing;")
    #cursor.execute("create table test_last (id int primary key auto_increment, name varchar(20))")
    #cursor.execute("INSERT INTO test_last (name) VALUES (?)", ['felix'])#.fetchall()
    #connection.commit()
    #cursor.execute("create table test (name varchar(20))")
    #cursor.execute("select last_insert_id()")
    #cursor.execute("show tables")
    cursor.execute("SELECT * FROM test_last")
    res = cursor.fetchone()
except mariadb.Error as e:
    print(e)


#for name, in res:
#    print(name)

#print(res[0])

#m_ids = [{k: item[k] for k in item.keys()} for item in res]

#for id in res:
#    print(id.get('name'))
print(res['name'])