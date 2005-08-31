import os, sys

def do(command):
    print command
    if os.system(command):
        sys.exit(1)


do('rm -rf SchoolTool-0.0.0*')
do('../../../zpkgtools/bin/zpkg -x reportlab -C SchoolTool.cfg')
do('tar xozf SchoolTool-0.0.0.tgz')
os.chdir('SchoolTool-0.0.0')
do('./configure --prefix `pwd`/z --with-python=%s' %sys.executable)
do('make install')
os.chdir('z')
do("bin/schooltooltest -vp1")
do("bin/mkschooltoolinst -d`pwd`/../i -u admin:123")
os.chdir('../i')
#do("bin/test")
do('bin/schooltool-server')
