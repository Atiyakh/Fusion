import time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sqlite3 as sql
import math

class Network:
    def __init__(self, initial_node, all_relationships):
        self.all_relationships = all_relationships
        self.relationships = []
        self.figured_nodes = []
        self.all_nodes = dict()
        self.initial_node = initial_node
        self.all_nodes[initial_node[0]] = initial_node
        self.current_node = initial_node
    
    def add_node(self, node):
        self.all_nodes[node[0]] = node
    
    def record_relationship(self, node):
        relationship = set([self.current_node[0], node[0]])
        if relationship not in self.all_relationships:
            self.relationships.append(relationship)
            self.all_relationships.append(relationship)
            return True
        else:
            return False
    
    def switch_current_node(self):
        self.figured_nodes.append(self.current_node)
        unsolved_nodes = [item for item in list(self.all_nodes.values()) if item not in self.figured_nodes]
        if unsolved_nodes:
            self.current_node = unsolved_nodes[0]
            return True
        else: # network figured
            return False

class ERDiagramViewer(QWidget):
    def clean_reference(self, structure: str, foreign_key=False):
        structure = structure.replace("(", " ")
        structure = structure.replace(")", " ")
        structure = structure.replace("[", " ")
        structure = structure.replace("]", " ")
        structure = structure.replace("\"", " ")
        structure = structure.replace("'", " ")
        structure = structure.replace("\n", " ")
        structure = structure.replace("\t", " ")
        structure = structure.replace("\r", " ")
        if foreign_key:
            if '.' in structure:
                structure = structure.split('.')[-1]
            return structure.strip()
        else:
            if 'on delete' in structure:
                structure = structure.split('on delete')[0]
            structure = [item for item in structure.split(' ') if item != ""]
            return tuple(structure)[:2]
    def extract_structure(self, sql_code: str):
        self.number_of_relationships += sql_code.lower().count("foreign key")
        general_structure = [
            [
                (
                    self.clean_reference(foreign_key.strip(), foreign_key=True),
                    self.clean_reference(reference.strip())
                )
                for foreign_key, reference in (structure.split(" references "),)
            ][0]
            for structure in sql_code.lower().split("foreign key")[1:]
        ]
        return general_structure
    def extract_tables(self):
        conn = sql.connect(self.database_path, check_same_thread=False)
        cur = conn.cursor()
        # with statement crying in the corner );
        cur.execute('SELECT sql, tbl_name FROM "main".sqlite_master WHERE type=?;', ('table',))
        for table_code, table_name in cur.fetchall():
            self.tables_names.append(table_name)
            if structure := self.extract_structure(table_code):
                self.tables_structures[table_name] = structure
            else:
                self.tables_structures[table_name] = [(None, (None, None))]
        cur.close()
        conn.close()

    def order_tables(self):
        structure_copy = self.tables_structures.copy()
        current_network = None
        structure_updated = False
        self.networks = []
        iterations = 0
        figured_relationships = 0
        while self.number_of_relationships > figured_relationships:
            iterations += 1
            if current_network:
                for table_name, relationships in self.tables_structures.items():
                    for relationship in relationships:
                        for current_node_relationship in current_network.current_node[1]:
                            if relationship[1][0] == current_network.current_node[0] or current_node_relationship[1][0] == table_name:
                                current_network.add_node(
                                    node=(table_name, relationships)
                                )
                                if current_network.record_relationship(
                                    current_network.all_nodes[table_name]
                                ):
                                    figured_relationships += 1
                                    structure_updated = True
            else:
                initial_table_name = list(structure_copy.keys())[0]
                initial_node = initial_table_name , structure_copy.pop(initial_table_name)
                current_network = Network(
                    initial_node=initial_node, all_relationships=self.all_relationships
                )
                self.networks.append(current_network)
                continue

            # prevent infinite recursion
            if iterations > 400:
                raise RecursionError(
                    "failed to come up with the right order; ER Diagram too complex to render"
                )

            if not current_network:
                if structure_copy:
                    # failed to come up with a network starting point
                    raise LookupError(
                        "failed find a starting point; ER Diagram too complex to render"
                    )
            # post-modeling check
            if structure_updated:
                structure_updated = False
            else: # switch network current_node
                if not current_network.switch_current_node():
                    current_network = None # start a new network if all nodes are figured
    
    def order_tables_2(self):
        for table_name in self.tables_names:
            for relationship in self.all_relationships:
                if table_name in relationship:
                    self.table_relationships_number[table_name] += 1
    
    def find_streams(self, table_name, stream=False):
        if not stream:
            all_streams = []
            stream = [table_name]
            for table_1, table_2 in self.all_relationships:
                if table_name in (table_1, table_2):
                    if table_1 == table_name: other_table = table_2
                    else: other_table = table_1
                    stream.append(other_table)
                    self.find_streams(other_table, all_stream)
        
    def find_longest_streamline(self):
        self.one_relationship_tables = []
        self.streams = []
        for table_name, number_of_relationships in self.table_relationships_number.items():
            if number_of_relationships == 1:
                self.one_relationship_tables.append(table_name)
        for table_name in self.one_relationship_tables:
            self.find_streams(table_name)


    def __init__(self, database_path):
        super().__init__()
        self.number_of_relationships = 0
        self.all_relationships = []
        self.table_relationships_number = dict()
        self.database_path = database_path
        self.tables_names = []
        self.tables_structures = dict()
        # extract tables
        self.extract_tables()
        for table_name in self.tables_names:
            self.table_relationships_number[table_name] = 0
        # ordering tables on the screen
        self.order_tables()
        self.order_tables_2()
        self.find_longest_streamline()

if __name__ == '__main__':
    app = QApplication([])
    main_window = QMainWindow()
    main_window.setCentralWidget(
        ERDiagramViewer(
            database_path="C:/Users/skhodari/Desktop/chinook.db"
        )
    )
    main_window.show()
    app.exec_()
