/* Setup template macros */

#define MASTER_ID "$Id: _zodb_btrees_IIBTree.c,v 1.1 2003/05/08 20:39:45 jim Exp $\n"

#define PERSISTENT

#define MOD_NAME_PREFIX "II"
#define INITMODULE init_zodb_btrees_IIBTree
#define DEFAULT_MAX_BUCKET_SIZE 120
#define DEFAULT_MAX_BTREE_SIZE 500

#include "intkeymacros.h"
#include "intvaluemacros.h"
#include "BTreeModuleTemplate.c"
