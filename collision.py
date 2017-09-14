import scgameobjects as scgo

def checkCollision(objA, objB):
    llAx, llAy = objA.getX(), (objA.getY() + objA.getHeight())
    llBx, llBy = objB.getX(), (objB.getY() + objB.getHeight())
    urAx, urAy = (objA.getX() + objA.getWidth()), objA.getY()
    urBx, urBy = (objB.getX() + objB.getWidth()), objB.getY()
    if isinstance(objA, scgo.Bullet):
        llAx = objA.getX() - objA.getWidth()
    if (urAy <= llBy) and (llAy >= urBy) and (urAx >= llBx) and (llAx <= urBx):
        return True
    return False
