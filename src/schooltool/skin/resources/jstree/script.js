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
              draggable: false,
            }
          }          
        });
        $('a.leaf_url').click(function() {
          document.location.href = $(this).attr("href");
        });
        $('.tree_list a[class!=leaf_url]').trigger('dblclick');
        $('.tree_list > ul > li > a').trigger('dblclick');
        $('.tree_list > ul > li:first-child > a').trigger('dblclick');
        $('.info-block li ul').css('border', '0');
      });
