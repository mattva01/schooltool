
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

    function status_parts(progress_id) {
        return {
            pending: $(ST.dialogs.jquery_id(progress_id+'-pending')),
            committing: $(ST.dialogs.jquery_id(progress_id+'-committing')),
            inprogress: $(ST.dialogs.jquery_id(progress_id+'-in-progress')),
            succeeded: $(ST.dialogs.jquery_id(progress_id+'-succeeded')),
            failed: $(ST.dialogs.jquery_id(progress_id+'-failed')),
        };
    }

    function on_progress_pending(progress_id, task_id, progress) {
        var parts = status_parts(progress_id);
        parts.committing.hide();
        parts.inprogress.hide();
        parts.succeeded.hide();
        parts.failed.hide();
        parts.pending.show();
        wait_to_poll(progress_id, task_id);
    }

    function update_progress_table(progress_id, part, progress) {
        var tbody = $(part).find('table tbody');
        for (var counter in progress.info) {
            var counter_id = progress_id+'-counter-'+counter;
            var row = tbody.find('tr[name="'+counter+'"]');
            if (row.length == 0) {
                part.find('table tbody:last').append($(
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
    }

    function on_progress_update(progress_id, task_id, progress) {
        var parts = status_parts(progress_id);
        parts.pending.hide();
        parts.committing.hide();
        parts.succeeded.hide();
        parts.failed.hide();
        update_progress_table(progress_id, parts.inprogress, progress);
        parts.inprogress.show();
        wait_to_poll(progress_id, task_id);
    }

    function on_progress_committing(progress_id, task_id, progress) {
        var parts = status_parts(progress_id);
        parts.pending.hide();
        parts.succeeded.hide();
        parts.failed.hide();
        update_progress_table(progress_id, parts.inprogress, progress);
        parts.inprogress.show();
        parts.committing.show();
        wait_to_poll(progress_id, task_id);
    }

    function on_progress_succeeded(progress_id, task_id, progress) {
        var parts = status_parts(progress_id);
        parts.pending.hide();
        parts.inprogress.hide('slow');
        parts.committing.hide();
        parts.failed.hide();

        if (progress.info.overall.errors.length) {
            var status = parts.succeeded.find('div[class="status"]');
            var error_templ = parts.succeeded.find('div[name="error-template"]');
            for (n in progress.info.overall.errors) {
                var error = progress.info.overall.errors[n];
                var new_error = $(error_templ.html());
                new_error.find('div[name="error"]').html(error);
                parts.succeeded.find('div[class="status"]:last').append(new_error);
                new_error.show();
            }
            status.show();
        }

        parts.succeeded.show();

        /* TODO: list xls errors on succesful import failure :) */
    }

    function on_progress_failed(progress_id, task_id, progress) {
        var parts = status_parts(progress_id);

        parts.failed.find('div[name="traceback"]').html(progress.traceback);
        parts.failed.find('div[name="info"]').html(progress.info);

        parts.pending.hide();
        parts.inprogress.hide('slow');
        parts.committing.hide();
        parts.succeeded.hide();
        parts.failed.show();
    }

    function progress_update_status(progress_id, task_id, progress) {
        var status = progress.status;
        if (status.pending) {
            on_progress_pending(progress_id, task_id, progress);
        } else if (status.committing) {
            on_progress_committing(progress_id, task_id, progress);
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
