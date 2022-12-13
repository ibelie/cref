class A(object): 
    pass

def test1(x):
    if x:
        a = A()
    else:
        a = 1

test1(False)




# class A(object):
#     pass
# class B(object):
#     pass
# class C(object):
#     pass

# def x():
#     a = A()
#     b = B()
#     c = C()

#     for p in [True, False]:
#         if p:
#             c = b
#             b.y = a
#         else:
#             a.x = c.y

# x()
