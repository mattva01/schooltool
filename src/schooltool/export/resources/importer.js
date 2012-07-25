
ST.export = $.extend(ST.export, {importer: function() {

  /* Private */

    function poll_progress(progress_id, task_id) {
          var url = ST.base_url+'schooltool.task_results/'+task_id;
          var request = $.ajax({
              type: "GET",
              url: url,
          }).success(function(result, textStatus, jqXHR){
              progress_update_status(progress_id, task_id, result);
          });
    }

    function wait_to_poll(progress_id, task_id) {
        setTimeout(function(){ poll_progress(progress_id, task_id); }, 1);
    }

    function on_progress_pending(progress_id, task_id, progress) {
        wait_to_poll(progress_id, task_id);
    }

    function on_progress_update(progress_id, task_id, progress) {
        var pending = $(ST.dialogs.jquery_id(progress_id+'-pending'));
        var inprogress = $(ST.dialogs.jquery_id(progress_id+'-in-progress'));
        pending.hide();

        var tbody = inprogress.find('table tbody');

        for (var counter in progress.info) {
            var counter_id = progress_id+'-counter-'+counter;
            var row = tbody.find('tr[name="'+counter+'"]');
            if (row.length == 0) {
                inprogress.find('table tbody:last').append($(
                    '<tr name="'+counter+'"><td name="title"></td><td width="80%"><div name="progress"></div></td></tr>'));
                row = tbody.find('tr[name="'+counter+'"]');
            }
            var counter_value = progress.info[counter].progress * 100;
            row.find('td[name="title"]').html(progress.info[counter].title);
                row.find('div[name="progress"]').progressbar({value:counter_value});

            if (progress.info[counter].active) {
                row.show();
            } else {
                row.hide();
            }
        }

        inprogress.show();
        wait_to_poll(progress_id, task_id);
    }

    function on_progress_succeeded(progress_id, task_id, progress) {
        var pending = $(ST.dialogs.jquery_id(progress_id+'-pending'));
        var inprogress = $(ST.dialogs.jquery_id(progress_id+'-in-progress'));
        var succeeded = $(ST.dialogs.jquery_id(progress_id+'-succeeded'));
        pending.hide();
        inprogress.hide('slow');
        succeeded.show();
    }

    function on_progress_failed(progress_id, task_id, progress) {
        var pending = $(ST.dialogs.jquery_id(progress_id+'-pending'));
        var inprogress = $(ST.dialogs.jquery_id(progress_id+'-in-progress'));
        var failed = $(ST.dialogs.jquery_id(progress_id+'-failed'));
        failed.find('div[name="traceback"]').html(progress.traceback);
        failed.find('div[name="info"]').html(progress.info);
        pending.hide();
        inprogress.hide('slow');
        failed.show();
    }

    function progress_update_status(progress_id, task_id, progress) {
        var status = progress.status;
        if (status.pending) {
            on_progress_pending(progress_id, task_id, progress);
        } else if (status.in_progress) {
            on_progress_update(progress_id, task_id, progress);
        } else if (status.succeeded) {
            on_progress_succeeded(progress_id, task_id, progress);
        } else if (status.failed) {
            on_progress_failed(progress_id, task_id, progress);
        }
    }

  /* Public */

  return {
      show_progress: function(progress_id, task_id) {
          poll_progress(progress_id, task_id);
      },

  }

}() } );
