from basenode import Node



class NodeFactory:
    @staticmethod
    def create(obj_type):
        if obj_type == "classe1":
            return Classe1()
        elif obj_type == "classe2":
            return Classe2()
        else:
            raise ValueError("Type inconnu")