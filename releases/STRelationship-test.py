import os, sys

def do(command):
    print command
    if os.system(command):
        sys.exit(1)


do('rm -rf STRelationship-0.0.0*')
do('../../../zpkgtools/bin/zpkg '
   '-x zope.app -C STRelationship.cfg')
do('tar xozf STRelationship-0.0.0.tgz')
os.chdir('STRelationship-0.0.0')
do('python setup.py install --home `pwd`/here')

zope3_path = os.path.abspath(os.curdir + '/../../Zope3/src')
st_path = os.path.abspath(os.curdir + '/here/lib/python')
exp = 'export PYTHONPATH=%s:%s' %(zope3_path, st_path)

os.chdir('here/lib/python')
tests_path = os.path.abspath(os.curdir + '/schooltool/relationship/tests')
for fn in os.listdir(tests_path):
    if fn.startswith('test') and fn.endswith('.py'):
        do('%s; python %s/%s' %(exp, tests_path, fn))
