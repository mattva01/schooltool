
#define MASTER_ID "$Id: _zodb_btrees_OOBTree.c,v 1.1 2003/05/08 20:39:45 jim Exp $\n"

#define PERSISTENT

#define MOD_NAME_PREFIX "OO"
#define INITMODULE init_zodb_btrees_OOBTree
#define DEFAULT_MAX_BUCKET_SIZE 30
#define DEFAULT_MAX_BTREE_SIZE 250
                                
#include "objectkeymacros.h"
#include "objectvaluemacros.h"
#include "BTreeModuleTemplate.c"
