
#define MASTER_ID "$Id: _zodb_btrees_OIBTree.c,v 1.1 2003/05/08 20:39:45 jim Exp $\n"

#define PERSISTENT

#define MOD_NAME_PREFIX "OI"
#define INITMODULE init_zodb_btrees_OIBTree
#define DEFAULT_MAX_BUCKET_SIZE 60
#define DEFAULT_MAX_BTREE_SIZE 250
                                
#include "objectkeymacros.h"
#include "intvaluemacros.h"
#include "BTreeModuleTemplate.c"
