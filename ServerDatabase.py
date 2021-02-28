import json
import sqlite3
import threading

from Block import Block


class ServerDatabase:
    class NodesAddressTable:
        """
        the NodesAddressTable consist of a table that has two parameters
        ip|port
        """

        def __init__(self, database_cursor: sqlite3.Cursor, connection: sqlite3.Connection):
            self.connection = connection
            self.cursor = database_cursor
            self.table_name = 'NodesAddressTable'
            self.create_table()

        def create_table(self):
            self.cursor.execute(
                f'''CREATE TABLE IF NOT EXISTS {self.table_name} (IP varchar(20) UNIQUE,PORT int);''')

    class BlockchainTable:
        """
        the Blockchain table consist of a table that has 12 parameters
        ID|parentID|SequenceNumber|Level|SecurityNumber|UploaderUsername|LBH(lastBlockHash)|CBH(CurrentBlockHash)|POW(proof of work)|TimeStamp|LOT(listOfTransactions)|LONW(ListOfNewUsers)
        """

        def __init__(self, database_cursor: sqlite3.Cursor, connection: sqlite3.Connection,
                     memory_cursor: sqlite3.Cursor, memory_connection: sqlite3.Connection, username: str = None,
                     is_first_node=False):
            self.username = username
            self.connection = connection
            self.cursor = database_cursor
            self.memory_cursor = memory_cursor
            self.memory_connection = memory_connection
            self.table_name = 'Blockchain'
            self.current_block_id = None  # temporary after create_table() it will change
            self.create_table()

            # TODO: intruduce my user by uploading a block
            #  that has the user in the new users part

            self.orphans_list = []  # list of all that has no origin

        def calculate_security_number_threshold(self) -> int:
            # TODO
            return 5



        def insert_block(self, block: Block):
            """
            this function is called only after it had been confirmed that the block has a father in the blockchain
            """
            if self.current_block_id != block.id:
                raise Exception('something ain''t right')
            command = f'''INSERT INTO Blockchain VALUES ({block.id},{block.parent_id},{block.sequence_number},{block.level},{block.security_number},"{block.uploader_username}","{block.last_block_hash}","{block.current_block_hash}","{block.proof_of_work}","{block.timestamp}","{json.dumps(block.list_of_transactions)}","{json.dumps(block.list_of_new_users)}")'''
            self.cursor.execute(command)
            self.memory_cursor.execute(command)
            self.current_block_id += 1

        def increase_block_security_number(self, blocks_id: int):
            """
             increase security number by 1
            """
            command = f'''UPDATE Blockchain SET SecurityNumber = SecurityNumber + 1 WHERE ID = {blocks_id} '''
            self.cursor.execute(command)
            self.memory_cursor.execute(command)

        def create_genesis_block(self):
            genesis_block = Block('genesis', [], [], '', '')
            genesis_block.set_table_parameters(self.current_block_id, 0, 1, 0)
            self.insert_block(genesis_block)

        def create_table(self):
            self.cursor.execute(f'''SELECT name FROM sqlite_master WHERE type='table' AND name='{self.table_name}';''')
            result = len(self.cursor.fetchall())
            create_table_command = f'''CREATE TABLE  {self.table_name} (ID INTEGER UNIQUE,ParentId INTEGER,SequenceNumber INTEGER,Level INTEGER,SecurityNumber INTEGER,UploaderUsername VARCHAR(256),LBH VARCHAR(257),CBH VARCHAR(257),POW VARCHAR(257), TimeStamp VARCHAR(255),LOT JSON,LONW JSON);'''
            if result == 0:  # aka table does not exist
                self.cursor.execute(create_table_command)
                self.memory_cursor.execute(create_table_command)

                self.current_block_id = 1  # default
                self.create_genesis_block()
            elif result == 1:  # aka table already exist

                # copying the table that already exist to  a table o memory{
                self.memory_cursor.execute(create_table_command)
                q = f'''SELECT * FROM Blockchain WHERE SecurityNumber <{self.calculate_security_number_threshold()}'''
                self.cursor.execute(q)
                list_of_all_blocks_to_memory = self.cursor.fetchall()
                for block in list_of_all_blocks_to_memory:
                    # TODO : check if works, if not then construct the string properly
                    q = f'''INSERT INTO Blockchain VALUES {block}'''
                    self.memory_cursor.execute(q)
                # }

                # setting the current block id {
                self.memory_cursor.execute(f'''Select * From Blockchain''')
                max_id = self.memory_cursor.fetchall()
                print(f'max id is {max_id}')
                self.current_block_id = max_id + 1
                # }

            else:
                raise Exception('duplicate tables')

    class UsersTable:
        MAX_BALANCE_DIGIT_LEN = 10
        MAX_BALANCE_DIGIT_LEN_AFTER_DOT = 10
        """
        the users table consist of a table that has three parameters
        username|publicKey|balance
        """""

        def __init__(self, database_cursor: sqlite3.Cursor, connection: sqlite3.Connection, username: str = None,
                     is_first_node=False):
            self.connection = connection
            self.cursor = database_cursor
            self.table_name = 'Users'
            self.create_table()

        def create_table(self):
            self.cursor.execute(
                f'''CREATE TABLE IF NOT EXISTS {self.table_name} (Username int UNIQUE,PublicKey varchar(256) UNIQUE,Balance DOUBLE({self.MAX_BALANCE_DIGIT_LEN}, {self.MAX_BALANCE_DIGIT_LEN_AFTER_DOT}));''')

        def get_balance(self, username: str) -> float:
            self.cursor.execute(f'''SELECT Balance FROM {self.table_name} WHERE Username='{username}';''')
            rows = self.cursor.fetchall()
            return rows[0][0]

        def get_public_key(self, username: str):
            self.cursor.execute(f'''SELECT PublicKey FROM {self.table_name} WHERE Username='{username}';''')
            rows = self.cursor.fetchall()
            return rows[0][0]

        def add_user(self, username: str, pk, balance: int = 0):
            s = f'''INSERT INTO {self.table_name} (Username, PublicKey, Balance) VALUES('{username}','{pk}', '{balance}');'''
            try:
                self.cursor.execute(s)
            except sqlite3.IntegrityError as e:
                print(e)
                pass

        def update_balance(self, username: str, new_balance):
            s = f'''UPDATE {self.table_name} SET Balance = {new_balance} WHERE Username = '{username}' '''
            self.cursor.execute(s)

    def __init__(self, username: str, is_first_node: bool):  # TODO: maybe delete is first node
        """
        :param username: username of the database
        """
        self.username = username
        self.database_name = username
        self.__connection, self.__memory_connection = self.connect_to_db()
        self.__cursor, self.__memory_cursor = self.__connection.cursor(), self.__memory_connection.cursor()
        self.__lock = threading.Lock()
        self.users_table = self.UsersTable(self.__cursor, self.__connection)
        self.blockchain_table = self.BlockchainTable(self.__cursor, self.__connection, self.__memory_cursor,
                                                     self.__memory_connection)

    def connect_to_db(self):
        return sqlite3.connect(f'{self.username}.db'), sqlite3.connect(':memory:')

    def acquire(self):
        self.__lock.acquire()

    def release(self):
        self.__connection.commit()
        self.__lock.release()

    def close(self):
        self.__connection.close()

    def print_data(self):
        command = f'''SELECT * FROM Blockchain'''
        self.__cursor.execute(command)
        self.__memory_cursor.execute(command)
        result = self.__cursor.fetchall()
        result_memory = self.__memory_cursor.fetchall()
        command = f'''SELECT  * FROM Users'''
        self.__cursor.execute(command)
        result_users = self.__cursor.fetchall()
        print(f'result {result}\nresult_memory {result_memory}\nresult_users {result_users}')

    def process_block(self, block: Block):
        """
        this function will be called every time a block has passed the threshold to be considered secure
        then and only then the block content will be taken in to account

        when prosseisng a block you need to first of all him and then to add all of the ney users to the table
        in order to solve situations that the uploader is a new user
        :return:
        """
        # TODO

    def add_block(self, block: Block) -> None:
        """
        all the checking is using the memory table but every change is being done to both tables

        :param block: the block to add to the database
        :return: None
        """
        # check if the block has a father
        self.blockchain_table.memory_cursor.execute(
            f'''SELECT * FROM Blockchain WHERE CBH = {block.last_block_hash} ''')
        list_of_fathers = self.blockchain_table.memory_cursor.fetchall()
        if len(list_of_fathers) == 0:  # aka block is an orphan
            pass
            # TODO: add block to orphan list
        elif len(list_of_fathers) == 1:  # aka found a father
            father = list_of_fathers[0]

            # add the block to the table
            my_id = self.blockchain_table.current_block_id
            my_parent_id = father[0]
            my_sequence_number = 0  # TODO
            my_level = father[4]
            my_security_number = 0
            block.set_table_parameters(my_id, my_parent_id, my_sequence_number, my_level, my_security_number)
            self.blockchain_table.insert_block(block)
            # }

            self.blockchain_table.memory_cursor.execute(
                f'''SELECT ID FROM Blockchain WHERE ParentId = {my_parent_id}''')
            list_of_brothers = self.blockchain_table.memory_cursor.fetchall()

            if len(list_of_brothers) == 1:  # aka i am the first son
                """
                here there are two options 
                1: I run and Update both the memory table and the one in the db but i stop when the updating finshed
                   on the memory table. it will be faster and more efficient 
                2: I do the same thing but i stop when the table in the db is finished (also the table on memory will finish).
                   It will take more time and as the chain keeps growing the time will increase in a liner line

                for now i choose option 1 but i am open for change
                """
                current_block = block
                while True:
                    command = f'''SELECT * FROM Blockchain WHERE ID = {current_block.parent_id} '''
                    self.blockchain_table.memory_cursor.execute(command)
                    father_block_list = self.blockchain_table.memory_cursor.fetchall()
                    if len(father_block_list) == 0:  # aka  I finished to update the entire memory table
                        break
                    elif len(father_block_list) == 1:
                        father_block = Block.create_block_from_tuple(father_block_list[0])
                        self.blockchain_table.increase_block_security_number(father_block)
                        current_block = father_block
                    else:
                        raise Exception('block has an unexpected amount of fathers')

                #  check if any blocks has passed the security threshold
                #  and remove any block that has an equal \ lower level the them{

                command = f'''SELECT * FROM Blockchain WHERE SecurityNumber > {self.blockchain_table.calculate_security_number_threshold()} '''
                self.blockchain_table.memory_cursor.execute(command)
                list_of_blocks_that_need_to_be_processed = self.blockchain_table.memory_cursor.fetchall()
                if len(list_of_blocks_that_need_to_be_processed) != 1:
                    raise Exception('more then one block has passed the threshold')
                block_to_process = Block.create_block_from_tuple(list_of_blocks_that_need_to_be_processed[0])
                self.process_block(block_to_process)
                # remove blocks that  became irrelevant
                command = f'''DELETE FROM Blockchain WHERE Level <= {block_to_process.level} '''
                self.blockchain_table.memory_cursor.execute(command)
                # }
            elif len(list_of_brothers) > 1:  # aka i am not the first son
                pass  # TODO: see if updating the SequenceNumber is relevant
            else:
                raise Exception(f'an unexpected amount of sons {len(list_of_brothers)}')
        else:
            raise Exception('block has an unexpected amount of fathers')
