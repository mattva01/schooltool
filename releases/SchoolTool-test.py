import os, sys

def do(command):
    print command
    if os.system(command):
        sys.exit(1)


do('rm -rf SchoolTool-0.0.0*')
do('../../../zpkgtools/bin/zpkg -C SchoolTool.cfg')
do('tar xozf SchoolTool-0.0.0.tgz')
os.chdir('SchoolTool-0.0.0')
do('./configure --prefix `pwd`/z --with-python=%s' %sys.executable)
do('make install')
os.chdir('z')
do("bin/schooltooltest -vp1")
# Use default username and password
do("bin/mkschooltoolinst -d`pwd`/../i1")
# Choose a username and password
do("bin/mkschooltoolinst -d`pwd`/../i2 -u admin:123")
os.chdir('../i2')
do("bin/test --testschooltool")
do('bin/schooltool-server')
