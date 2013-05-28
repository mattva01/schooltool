
ST.task = $.extend(ST.task, {progress: function() {

  /* Private */

    function reload_dialog(progress_id) {
        var form_selector = $(ST.dialogs.jquery_id(progress_id+'-progress-form'));
        var button_selector = $(ST.dialogs.jquery_id(progress_id+'-refresh-button'));
        ST.dialogs.submit(form_selector, button_selector);
    }

    function poll_progress(progress_id, task_id, prev_state, should_reload) {
          var url = ST.base_url+'schooltool.task_results/'+task_id;
          var request = $.ajax({
              type: "GET",
              url: url,
          }).success(function(result, textStatus, jqXHR){
              if (should_reload === undefined) {
                  should_reload = true;
              }
              progress_update_status(progress_id, task_id, result, prev_state, should_reload);
          });
    }

    function wait_to_poll(progress_id, task_id, progress) {
        setTimeout(function(){ poll_progress(progress_id, task_id, progress.internal_state); }, 0.25);
    }

    function on_progress_pending(progress_id, task_id, progress) {
        wait_to_poll(progress_id, task_id, progress);
    }

    function update_progress_table(progress_id, part, progress) {
        var tbody = $(part).find('table tbody');
        for (var counter in progress.info.lines) {
            var counter_id = progress_id+'-counter-'+counter;
            var row = tbody.find('tr[name="'+counter+'"]');
            if (row.length == 0) {
                part.find('table tbody:last').append($(
                    '<tr name="'+counter+'"><td name="title"></td><td width="80%"><div name="progress"></div></td></tr>'));
                row = tbody.find('tr[name="'+counter+'"]');
            }
            var title_td = row.find('td[name="title"]')
            title_td.html(progress.info.lines[counter].title);
            if (progress.info.lines[counter].progress == null) {
                title_td.attr('colspan', 2);
            } else {
                title_td.attr('colspan', 1);
                var counter_value = progress.info.lines[counter].progress * 100;
                row.find('div[name="progress"]').progressbar({value:counter_value});
            }
            if (progress.info.lines[counter].active) {
                row.show();
            } else {
                row.hide();
            }
        }
    }

    function on_progress_update(progress_id, task_id, progress) {
        var part = $(ST.dialogs.jquery_id(progress_id+'-progress'));
        update_progress_table(progress_id, part, progress);
        wait_to_poll(progress_id, task_id, progress);
    }

    function on_progress_committing(progress_id, task_id, progress) {
        var part = $(ST.dialogs.jquery_id(progress_id+'-progress'));
        update_progress_table(progress_id, part, progress);
        wait_to_poll(progress_id, task_id, progress);
    }

    function progress_update_status(progress_id, task_id, progress, prev_state, should_reload) {
        var status = progress.status;

        if (progress.info && progress.info.title) {
            var part = $(ST.dialogs.jquery_id(progress_id+'-progress-title'));
            part.html(progress.info.title);
        }

        if (status.pending) {
            on_progress_pending(progress_id, task_id, progress);
        } else if (status.committing) {
            on_progress_committing(progress_id, task_id, progress);
        } else if (status.in_progress) {
            on_progress_update(progress_id, task_id, progress);
        } else if (status.succeeded) {
            if (should_reload) {
                reload_dialog(progress_id);
            }
        } else if (status.failed) {
            if (should_reload) {
                reload_dialog(progress_id);
            }
        }
    }

  /* Public */

  return {
      show_progress: function(progress_id, task_id, should_reload) {
          poll_progress(progress_id, task_id, undefined, should_reload);
      },

  }

}() } );
