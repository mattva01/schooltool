import os, sys

def do(command):
    print command
    if os.system(command):
        sys.exit(1)


do('rm -rf STRelationship-0.0.0*')
do('../../../zpkgtools/bin/zpkg '
   '-C STRelationship.cfg STRelationship')
do('tar xozf STRelationship-0.0.0.tgz')
os.chdir('STRelationship-0.0.0')
do('python setup.py install --prefix here')
