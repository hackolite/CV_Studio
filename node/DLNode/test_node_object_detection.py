import pytest
from node.deep_learning_node.node_object_detection import *




def test_init_node():
	instance  = Node()


def test_add_node():
	print("test")
	instance  = Node()
	node_id = 10

	try:
		instance.add_node("MOCK", node_id, pos=[0, 0],opencv_setting_dict=None,callback=None)
		return True

	except Exception as e:
 		return False


def test_update_node():
    pass
    #assert division(10, 2) == 5
    #assert division(-10, 2) == -5
    #with pytest.raises(ValueError):
    #    division(10, 0)

