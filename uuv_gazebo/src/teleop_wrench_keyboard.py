#!/usr/bin/env python
 
 
#importing the necessary functions to the node
from __future__ import print_function
from logging import fatal
 
import threading
 
import roslib; roslib.load_manifest('teleop_twist_keyboard')
import rospy
 
from geometry_msgs.msg import Twist
#importing Wrench to use it as the message type sent by the node
from geometry_msgs.msg import Wrench
 
import sys, select, termios, tty
 
msg = """
Reading from the keyboard  and Publishing to Twist!
---------------------------
Moving around:
  u    i    o
  j    k    l
  m    ,    .
 
For Holonomic mode (strafing), hold down the shift key:
---------------------------
  U    I    O
  J    K    L
  M    <    >
 
t : up (+z)
b : down (-z)
 
anything else : stop
 
q/z : increase/decrease max speeds by 10%
w/x : increase/decrease only linear speed by 10%
e/c : increase/decrease only angular speed by 10%
 
CTRL-C to quit
"""
# multiplying by 10 the values compared to the original
# teleop_twist_keyboard node to see some change while using
# forces and torques
 
moveBindings = {
       'i':(10,0,0,0),
       'o':(10,0,0,-10),
       'j':(0,0,0,10),
       'l':(0,0,0,-10),
       'u':(10,0,0,10),
       ',':(-10,0,0,0),
       '.':(-10,0,0,10),
       'm':(-10,0,0,-10),
       'O':(10,-10,0,0),
       'I':(10,0,0,0),
       'J':(0,10,0,0),
       'L':(0,-10,0,0),
       'U':(10,10,0,0),
       '<':(-10,0,0,0),
       '>':(-10,-10,0,0),
       'M':(-10,10,0,0),
       't':(0,0,10,0),
       'b':(0,0,-10,0),
   }
 
speedBindings={
       'q':(1.1,1.1),
       'z':(.9,.9),
       'w':(1.1,1),
       'x':(.9,1),
       'e':(1,1.1),
       'c':(1,.9),
   }
 
 
 
class PublishThread(threading.Thread):
   def __init__(self, rate):
       super(PublishThread, self).__init__()
       # setting the right topic to which this node should publish
       self.publisher = rospy.Publisher('/rexrov/thruster_manager/input', Wrench, queue_size = 1)
       self.x = 0.0
       self.y = 0.0
       self.z = 0.0
       self.ta = 0.0
       # using additional variables compated to the original node
       self.tb = 0.0
       self.th = 0.0
       self.speed = 0.0
       self.turn = 0.0
       self.condition = threading.Condition()
       self.done = False
 
       # Set timeout to None if rate is 0 (causes new_message to wait forever
       # for new data to publish)
       if rate != 0.0:
           self.timeout = 1.0 / rate
       else:
           self.timeout = None
 
       self.start()
 
   def wait_for_subscribers(self):
       i = 0
       while not rospy.is_shutdown() and self.publisher.get_num_connections() == 0:
           if i == 4:
               print("Waiting for subscriber to connect to {}".format(self.publisher.name))
           rospy.sleep(0.5)
           i += 1
           i = i % 5
       if rospy.is_shutdown():
           raise Exception("Got shutdown request before subscribers connected")
 
   def update(self, x, y, z, ta, tb, th):
       self.condition.acquire()
       self.x = x
       self.y = y
       self.z = z
       self.ta = ta
       self.tb = tb
       self.th = th
       self.speed = speed  
       self.turn = turn
       self.condition.notify()
       self.condition.release()
 
   def stop(self):
       self.done = True
       self.update(0, 0, 0, 0, 0, 0)
       self.join()
 
   def run(self):
       # changing here the nature of the message sent compared to the
       # original node from twist to wrench
       wrench = Wrench()
       while not self.done:
           self.condition.acquire()
           # Wait for a new message or timeout.
           self.condition.wait(self.timeout)
 
           # Copy state into wrench message.
           wrench.linear.x = self.x * self.speed
           wrench.linear.y = self.y * self.speed
           wrench.linear.z = self.z * self.speed
           wrench.angular.x = self.ta * self.turn
           wrench.angular.y = self.tb * self.turn
           wrench.angular.z = self.th * self.turn
 
           self.condition.release()
 
           # Publish.
           self.publisher.publish(wrench)
 
       # Publish stop message when thread exits.
       wrench.linear.x = 0
       wrench.linear.y = 0
       wrench.linear.z = 0
       wrench.angular.x = 0
       wrench.angular.y = 0
       wrench.angular.z = 0
       self.publisher.publish(wrench)
 
 
def getKey(key_timeout):
   tty.setraw(sys.stdin.fileno())
   rlist, _, _ = select.select([sys.stdin], [], [], key_timeout)
   if rlist:
       key = sys.stdin.read(1)
   else:
       key = ''
   termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
   return key
 
 
if __name__=="__main__":
   # updated main function with the additional paramters
   settings = termios.tcgetattr(sys.stdin)
 
   rospy.init_node('teleop_wrench_keyboard')
 
   # check if we need those parameters or need to rename them
   speed = rospy.get_param("~speed", 0.5)
   turn = rospy.get_param("~turn", 1.0)
   repeat = rospy.get_param("~repeat_rate", 0.0)
   key_timeout = rospy.get_param("~key_timeout", 0.0)
   if key_timeout == 0.0:
       key_timeout = None
 
   pub_thread = PublishThread(repeat)
 
   x = 0
   y = 0
   z = 0
   ta = 0
   tb = 0
   th = 0
   status = 0
 
   try:
       pub_thread.wait_for_subscribers()
       pub_thread.update(x, y, z, ta, tb, th, speed, turn)
 
       print(msg)
       #print(vels(speed,turn))
       while(1):
           key = getKey(key_timeout)
           if key in moveBindings.keys():
               x = moveBindings[key][0]
               y = moveBindings[key][1]
               z = moveBindings[key][2]
               ta = moveBindings[key][3]
               tb = moveBindings[key][4]
               th = moveBindings[key][5]
           elif key in speedBindings.keys():
               speed = speed * speedBindings[key][0]
               turn = turn * speedBindings[key][1]
 
              
               if (status == 14):
                   print(msg)
               status = (status + 1) % 15
           else:
               # Skip updating cmd_vel if key timeout and robot already
               # stopped.
               if key == '' and x == 0 and y == 0 and z == 0 and ta==0 and tb==0 and th == 0:
                   continue
               x = 0
               y = 0
               z = 0
               ta = 0
               tb = 0
               th = 0
               if (key == '\x03'):
                   break
           pub_thread.update(x, y, z, ta, tb, th, speed, turn)
 
   except Exception as e:
       print(e)
 
   finally:
       pub_thread.stop()
 
       termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)