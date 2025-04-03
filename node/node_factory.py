from node import *



class NodeFactory:
    @classmethod
    def create(cls, node_classe):
        if obj_type == "classe1":
            return Classe1()
        elif obj_type == "classe2":
            return Classe2()
        else:
            raise ValueError("Type inconnu")
        return instance