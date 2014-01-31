$(document).ready(function () {
    $('.tree_list').tree({
        ui: {
            theme_name: 'classic'
        },
        types: {
            'default': {
                clickable: false,
                renameable: false,
                deletable: false,
                creatable: false,
                draggable: false
            }
        },
        callback: {
            onload: function(tree) {
                tree.open_all();
                tree.close_branch('.tree .inactive');
            }
        }
    });
    $('a.leaf_url').click(function() {
        document.location.href = $(this).attr("href");
    });
});
