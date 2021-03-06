#!/usr/bin/env python

import rospy
import numpy as np
import tf

from std_msgs.msg import String
from geometry_msgs.msg import Twist, Point, Quaternion, Pose, PoseStamped, PoseWithCovarianceStamped
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid, MapMetaData, Path
from visualization_msgs.msg import Marker

#TODO:add threading
#TODO:use initial position from amcl node

class Node_end():
    """
    A node class for A* Pathfinding
    @parameter parent: parent node
    @parameter position: position on map
    @parameter g: cost from start position to current position
    @parameter h: heuristic cost from current position to goal
    @parameter f: sum of g and h
    """

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position

class Node_start():
    """
    A node class for A* Pathfinding
    @parameter parent: parent node
    @parameter position: position on map
    @parameter g: cost from start position to current position
    @parameter h: heuristic cost from current position to goal
    @parameter f: sum of g and h
    """

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position

class Bidirectional_Astar_Planner():
    """
    Independent Astar_Planner function class
    """
    def check_obstacle(self, start, end):
        """
        This function is used to check if there is an obstacle between start point and end point

        @return True: if there is an obstacle between start and end
        @return False: if there is no obstacle between start and end
        """

        # get the difference between start and end in x,y axis
        disx = -(start[0] - end[0])
        disy = -(start[1] - end[1])

        # The circumstance that difference in x axis is bigger
        if abs(disx) > abs(disy):

            # disx is larger than 0
            if disx > 0:
                for i in range(disx):
                    x = start[0] + i
                    y = int(start[1] + i * disy / disx)
                    if self.map[x][y] > 50:
                        return True
                return False

            # disx is smaller than 0
            else:
                for i in range(-disx):
                    x = start[0] - i
                    y = int(start[1] + i * disy / (-disx))
                    if self.map[x][y] > 50:
                        return True
                return False

        # The circumstance that difference in y axis is bigger
        else:

            # disy is larger than 0
            if disy > 0:
                for i in range(disy):
                    x = int(start[0] + i * disx / disy)
                    y = start[1] + i
                    if self.map[x][y] > 50:
                        return True
                return False

            # disy is smaller than 0
            else:
                for i in range(-disy):
                    x = int(start[0] + i * disx / (-disy))
                    y = start[1] - i
                    if self.map[x][y] > 50:
                        return True
                return False

    def get_key_point(self, path):
        """
        This function is used to delete non-neccessary point in path

        @return: path with only key point
        """
        # set new path begin at path[0]
        new_path = [path[0]]

        # determine if the moving direction changes, if it does not change, delete the point in middle
        length_path = len(path)
        for i in range(2,length_path - 1):
            vector1 = (path[i-1][0] - path[i-2][0], path[i-1][1] - path[i-2][1])
            vector2 = (path[i][0] - path[i-1][0], path[i][1] - path[i-1][1])
            if vector1 != vector2:
                new_path.append(path[i-1])

        # at last, add the last element in path to new path
        new_path.append(path[length_path - 1])
        return new_path

    def Path_smoothing(self, path):
        """
        This is a function to smooth path. To make a path looks more realistic.
        """
        # First merge nodes that the direction do not change, keep key nodes only
        path = self.get_key_point(path)

        # Second using Floyed method to smooth path
        l = len(path)
        i = 0

        # if the path only contains two key points, return the path
        if l == 2:
            return path

        # apply path smoothing function
        while True:
            while not self.check_obstacle(path[i], path[i+2]):
                path.pop(i + 1)
                l = len(path)
                if i == l - 2:
                    break
            i += 1
            if i > l - 3:
                break
        return path

    def Path_argument(self, path):
        """
        This is a function to make path consists of only key points to dense path
        """
        # set a new path
        new_path = []

        # main function of path argument
        length = len(path)
        i = 0
        while True:

            # break rule
            if i == length - 1:
                break

            # difference in x,y axis
            disx = -(path[i][0] - path[i+1][0])
            disy = -(path[i][1] - path[i+1][1])

            # if the two key points can directly connected, then pass
            if abs(disy) == 1 and abs(disy) == 1:
                pass

            # if there must be other grids between two key points
            # The circumstance that difference in x axis is bigger
            if abs(disx) > abs(disy):
                # disx is larger than 0
                if disx > 0:
                    for j in range(disx):
                        x = path[i][0] + j
                        y = int(path[i][1] + j * disy / disx)
                        new_path.append((x, y))
                # disx is smaller than 0
                else:
                    for j in range(-disx):
                        x = path[i][0] - j
                        y = int(path[i][1] + j * disy / (-disx))
                        new_path.append((x, y))
            # The circumstance that difference in y axis is bigger
            else:
                # disy is larger than 0
                if disy > 0:
                    for j in range(disy):
                        x = int(path[i][0] + j * disx / disy)
                        y = path[i][1] + j
                        new_path.append((x, y))
                # disy is smaller than 0
                else:
                    for j in range(-disy):
                        x = int(path[i][0] + j * disx / (-disy))
                        y = path[i][1] - j
                        new_path.append((x, y))
            i += 1
        return new_path

    def check_direction(self, node_child, node_parent):
        """
        check the direction of next step
        if the direction does not change, return 0
        if the direction changes, return 1
        """
        node_grand = node_parent.parent
        if not node_grand:
            return 0
        vector1 = (node_child.position[0] - node_parent.position[0], node_child.position[1] - node_parent.position[1])
        vector2 = (node_parent.position[0] - node_grand.position[0], node_parent.position[1] - node_grand.position[1])
        if vector1 == vector2:
            return 0
        return 5

    def getMinNode(self, input_list):
        """
        try to find the node with minimal f in openlist

        @return: the node with minimal f value
        """
        currentNode = input_list[0]
        for node in input_list:
            if node.f < currentNode.f:
                currentNode = node
        return currentNode

    def pointInCloseList(self, position, closed_list):
        """
        determine if a position is in closelist
        """
        for node in closed_list:
            if node.position == position:
                return True
        return False

    def pointInOpenList(self, position, open_list):
        """
        determine if a position is in openlist
        """
        for node in open_list:
            if node.position == position:
                return node
        return None

    def check_intersection(self, open_start, open_end):
        """
        find intersection part of two openlist
        """
        for node in open_start:
            append = self.pointInOpenList(node.position, open_end)
            if append:
                self.intersect.append(append.position)
        return self.intersect

    def search_start(self, minF, offsetX, offsetY):
        """
        search action for next step and add this node to openlist
        """

        node_pos = (minF.position[0] + offsetX, minF.position[1] + offsetY)

        # if the offset is out of boundary
        if node_pos[0] > self.map_width - 1 or node_pos[0] < 0 or node_pos[1] > self.map_height - 1 or node_pos[1] < 0:
            return

        # if the node is in closed set, then pass
        elif self.pointInCloseList(node_pos, self.closed_list_start):
            return

        else:
            # if it is not in openlist, add it to openlist
            currentNode = self.pointInOpenList(node_pos, self.open_list_start)
            if not currentNode:
                currentNode = Node_start(minF, node_pos)
                currentNode.g = minF.g + np.sqrt(offsetX * offsetX + offsetY * offsetY)
                dx = abs(node_pos[0] - self.endnode.position[0])
                dy = abs(node_pos[1] - self.endnode.position[1])
                turn_cost = self.check_direction(currentNode, minF)
                # closed-form distance
                # currentNode.h =  dx + dy + (np.sqrt(2) - 2) * min(dx, dy) + self.map[node_pos[0]][node_pos[1]]
                # euclidean distance
                currentNode.h =  dx + dy + self.map[node_pos[0]][node_pos[1]] * 0.9 + turn_cost
                # real distance
                # currentNode.h =  np.sqrt(dx * dx + dy * dy) + self.map[node_pos[0]][node_pos[1]]
                currentNode.f = currentNode.g + currentNode.h
                self.open_list_start.append(currentNode)
                return
            # if it is in openlist, determine if g of currentnode is smaller
            else:
                action_cost = np.sqrt(offsetX * offsetX + offsetY * offsetY)
                if minF.g + action_cost < currentNode.g:
                    currentNode.g = minF.g + action_cost
                    currentNode.parent = minF
                    return

    def search_end(self, minF, offsetX, offsetY):
        """
        search action for next step and add this node to openlist
        """

        node_pos = (minF.position[0] + offsetX, minF.position[1] + offsetY)

        # if the offset is out of boundary
        if node_pos[0] > self.map_width - 1 or node_pos[0] < 0 or node_pos[1] > self.map_height - 1 or node_pos[1] < 0:
            return

        # if the node is in closed set, then pass
        elif self.pointInCloseList(node_pos, self.closed_list_end):
            return

        else:
            # if it is not in openlist, add it to openlist
            currentNode = self.pointInOpenList(node_pos, self.open_list_end)
            if not currentNode:
                currentNode = Node_end(minF, node_pos)
                currentNode.g = minF.g + np.sqrt(offsetX * offsetX + offsetY * offsetY)
                dx = abs(node_pos[0] - self.startnode.position[0])
                dy = abs(node_pos[1] - self.startnode.position[1])
                turn_cost = self.check_direction(currentNode, minF)
                # closed-form distance
                # currentNode.h =  dx + dy + (np.sqrt(2) - 2) * min(dx, dy) + self.map[node_pos[0]][node_pos[1]]
                # euclidean distance
                currentNode.h =  dx + dy + self.map[node_pos[0]][node_pos[1]] * 0.9 + turn_cost
                # real distance
                # currentNode.h =  np.sqrt(dx * dx + dy * dy) + self.map[node_pos[0]][node_pos[1]]
                currentNode.f = currentNode.g + currentNode.h
                self.open_list_end.append(currentNode)
                return
            # if it is in openlist, determine if g of currentnode is smaller
            else:
                action_cost = np.sqrt(offsetX * offsetX + offsetY * offsetY)
                if minF.g + action_cost < currentNode.g:
                    currentNode.g = minF.g + action_cost
                    currentNode.parent = minF
                    return

    def bi_astar(self, gridmap, map_width, map_height, start, end):
        """
        main function of astar search

        @return: a global path
        """

        # Initialize endnode and startnode
        self.startnode = Node_start(None, start)
        self.startnode.g = self.startnode.h = self.startnode.f = 0
        self.endnode = Node_end(None, end)
        self.endnode.g = self.endnode.h = self.endnode.f = 0
        self.map = gridmap
        self.map_width = map_width
        self.map_height = map_height

        # Initialize open and closed list
        self.open_list_start = [self.startnode] # store f of next possible step
        self.closed_list_start = [] # store f of minimal path
        self.open_list_end = [self.endnode]
        self.closed_list_end = []
        self.intersect = []
        start = True

        # try to find the path with minimal cost
        while True:

            # find the node with minimal f in openlist
            minF_start = self.getMinNode(self.open_list_start)
            minF_end = self.getMinNode(self.open_list_end)

            # add this node to closed_list and delete this node from open_list
            self.closed_list_start.append(minF_start)
            self.open_list_start.remove(minF_start)
            self.closed_list_end.append(minF_end)
            self.open_list_end.remove(minF_end)

            # apply search to add node for next step in 8 directions
            self.search_end(minF_end, 0, 1)
            self.search_end(minF_end, 1, 0)
            self.search_end(minF_end, 0, -1)
            self.search_end(minF_end, -1, 0)
            self.search_end(minF_end, 1, 1)
            self.search_end(minF_end, 1, -1)
            self.search_end(minF_end, -1, 1)
            self.search_end(minF_end, -1, -1)

            self.search_start(minF_start, 0, 1)
            self.search_start(minF_start, 1, 0)
            self.search_start(minF_start, 0, -1)
            self.search_start(minF_start, -1, 0)
            self.search_start(minF_start, 1, 1)
            self.search_start(minF_start, 1, -1)
            self.search_start(minF_start, -1, 1)
            self.search_start(minF_start, -1, -1)

            self.intersect = self.check_intersection(self.open_list_start, self.open_list_end)
            if self.intersect:
                # get the intersection position with minimal f value
                minpos = self.intersect[0]
                current_f = self.pointInOpenList(minpos, self.open_list_start).f + self.pointInOpenList(minpos, self.open_list_end).f
                for pos in self.intersect:
                    node_start = self.pointInOpenList(pos, self.open_list_start)
                    node_end = self.pointInOpenList(pos, self.open_list_end)
                    f = node_start.f + node_end.f
                    if f < current_f:
                        current_f = f
                        minpos = pos

                #generate path
                path = []
                current = self.pointInOpenList(minpos, self.open_list_end)
                while current is not None:
                    path.append(current.position)
                    current = current.parent
                path = path[1:]
                path = path[::-1]
                current = node_start
                while current is not None:
                    path.append(current.position)
                    current = current.parent

                # apply path smoothing function
                path = self.Path_smoothing(path)

                # apply path argument function
                path = self.Path_argument(path)

                # return path
                return path[::-1]

class main():
    """
    implement of global planner, neccessary subscribers and publishers
    """

    def __init__(self):

        # Initialize Subscribers
        rospy.wait_for_message('/global_costmap', OccupancyGrid)
        # self.sub_map = rospy.Subscriber('/move_base/global_costmap/costmap', OccupancyGrid, self.callback_costmap)
        self.sub_map = rospy.Subscriber('/global_costmap', OccupancyGrid, self.callback_costmap)
        self.sub_pos = rospy.Subscriber('/pose', PoseStamped, self.callback_pos)
        # self.sub_pos = rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, self.callback_pos)
        self.sub_goal = rospy.Subscriber('/move_base_simple/goal', PoseStamped, self.callback_goal)

        # Initialize Publisher
        self.pub_path = rospy.Publisher('/global_path', Path, queue_size=10)
        self.pub_plan = rospy.Publisher('/visualization/plan', Marker, queue_size=10)
        # self.pub_cmd = rospy.Publisher('/cmd_vel',Twist, queue_size=10)

        # Initialize messages
        self.msg_path = Path()
        self.msg_path.header.stamp = rospy.Time.now()
        self.msg_path.header.frame_id = "path"

        self.msg_path_marker = Marker()
        self.msg_path_marker.header.frame_id = "map"
        self.msg_path_marker.ns = "navigation"
        self.msg_path_marker.id = 0
        self.msg_path_marker.type = Marker.LINE_STRIP
        self.msg_path_marker.action = Marker.ADD
        self.msg_path_marker.scale.x = 0.1
        self.msg_path_marker.color.a = 0.5
        self.msg_path_marker.color.r = 0.0
        self.msg_path_marker.color.g = 0.0
        self.msg_path_marker.color.b = 1.0
        self.msg_path_marker.pose.orientation = Quaternion(0, 0, 0, 1)

    def callback_costmap(self, OccupancyGrid):
        """
        callback of costmap
        """
        self.map_input = np.array(OccupancyGrid.data)
        self.map_width = OccupancyGrid.info.width
        self.map_height = OccupancyGrid.info.height
        self.map = self.map_input.reshape(self.map_height, self.map_width) # shape of 169(width)*116(height)
        self.map = np.transpose(self.map)
        self.origin = OccupancyGrid.info.origin.position
        self.resolution = OccupancyGrid.info.resolution

    # Wait for amcl part to provide it with initial position
    def callback_pos(self, PoseStamped):
        """
        callback of position
        """
        # self.pos_x = int((PoseWithCovarianceStamped.pose.pose.position.x - self.origin.x) / self.resolution)
        # self.pos_y = int((PoseWithCovarianceStamped.pose.pose.position.y - self.origin.y) / self.resolution)
        self.pos_x = int((PoseStamped.pose.position.x - self.origin.x) / self.resolution)
        self.pos_y = int((PoseStamped.pose.position.y - self.origin.y) / self.resolution)
        # self.posx = PoseWithCovarianceStamped.pose.pose.position.x
        # self.posy = PoseWithCovarianceStamped.pose.pose.position.y
        # print(self.posx, self.posy)

    def callback_goal(self, PoseStamped):
        """
        callback of goal
        """
        # shift position to position in map
        self.goal_x = int((PoseStamped.pose.position.x - self.origin.x) / self.resolution)
        self.goal_y = int((PoseStamped.pose.position.y - self.origin.y) / self.resolution)
        # print(PoseStamped.pose.position.x, PoseStamped.pose.position.y)
        # print('goal is ',self.goal_x, self.goal_y)

    def check_valid(self, goalx, goaly):
        """
        check the validility of goal
        """
        if goalx > self.map_width - 1 or goalx < 0 or goaly > self.map_height - 1 or goaly < 0:
            # rospy.logwarn('Goal is out of boundary')
            return None
        elif self.map[int(goalx)][int(goaly)] < 90 and self.map[int(goalx)][int(goaly)] > -1:
            return True
        else:
            return None

    # run astar node
    def run(self, rate: float = 1):

        while not rospy.is_shutdown():

            # wait for goal input to start global planner
            rospy.wait_for_message('/move_base_simple/goal', PoseStamped)
            global_planner = Bidirectional_Astar_Planner()

            # initialize start node
            #TODO:replace initial position using amcl
            # self.pos_x = int((0.09035 - self.origin.x) / self.resolution)
            # self.pos_y = int((0.01150 - self.origin.y) / self.resolution)
            start = (self.pos_x, self.pos_y)
            # print('start is ',self.posx, self.posy)

            if self.check_valid(self.goal_x, self.goal_y):

                end = (int(self.goal_x), int(self.goal_y))
                path = global_planner.bi_astar(self.map, self.map_width, self.map_height, start, end)

                # publish path
                for pa in path:
                    pose = PoseStamped()
                    pose.pose.position.x = (pa[0] + 0.5) * self.resolution + self.origin.x
                    pose.pose.position.y = (pa[1] + 0.5) * self.resolution + self.origin.y
                    self.msg_path_marker.points.append(Point(pose.pose.position.x, pose.pose.position.y, 0))
                    self.msg_path.poses.append(pose)
                self.pub_plan.publish(self.msg_path_marker)
                self.pub_path.publish(self.msg_path)
                self.msg_path.poses.clear()
                self.msg_path_marker.points.clear()
                rospy.loginfo('Path is published')

            else:
                rospy.loginfo('Goal is not valid')



if __name__ == "__main__":
   rospy.init_node('rto_global_planner')

   main = main()
   main.run(rate=10)