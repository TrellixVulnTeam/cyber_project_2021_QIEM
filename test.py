import hashlib

from Block import Block
from Constants import MAX_NONCE
from ServerDatabase import ServerDatabase
from Transaction import Transaction
from User import User


def proof_of_work(block_as_str: str, difficulty_bits: int):
    target = 2 ** (256 - difficulty_bits)
    for nonce in range(MAX_NONCE):
        input_to_hash = block_as_str + str(nonce)
        hash_result = hashlib.sha256(input_to_hash.encode()).hexdigest()

        if int(hash_result, 16) < target:
            return nonce

    return nonce


genesis_block = Block('genesis', [], [], '', '')
diff = 15


def create_new_block(username, LOT, LONW, LB: Block):
    b1 = Block(username, LOT, LONW, LB.current_block_hash)
    b1.proof_of_work = proof_of_work(LB.as_str(), diff)
    return b1


s = ServerDatabase('tal', True)

s.acquire()
b = create_new_block('name1', [], [User('name1', 'fdsf'), User('tal', 'fd4ab'), User('Ofek', '32')], genesis_block)
s.add_block(b)
s.print_data()
s.release()

s.acquire()

b = create_new_block('name2', [Transaction('name1', 'Ofek', 1.2, 'becaue im a goat')], [User('name2', '123')], b)
s.add_block(b)
s.print_data()
s.release()

s.acquire()

b = create_new_block('name3', [], [User('name3', '12r3')], b)
s.add_block(b)
s.print_data()
s.release()

s.acquire()
b = create_new_block('name1', [], [User('name4', '12433')], b)
s.add_block(b)
s.print_data()
s.release()

s.acquire()
b = create_new_block('name5', [], [User('name5', '1235')], b)
s.add_block(b)
s.print_data()
s.release()

s.acquire()
b = create_new_block('name6', [], [User('name6', '12345')], b)
s.add_block(b)
s.print_data()
s.release()

s.acquire()
b = create_new_block('name7', [], [User('name7', '12355')], b)
s.add_block(b)
s.print_data()
s.release()

s.close()
