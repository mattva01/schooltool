ST.report = function () {
    function get_filter_fields() {
        return $('.report-filter');
    };
    function get_filter_field_values(fields) {
        var result = [],
            field;
        fields.each(function(index, element) {
            field = $(element);
            if (field.is('select') || field.is('input:checked')) {
                result.push({
                    name: field.attr('name'),
                    value: field.val()
                });
            }
        });
        return result;
    };
    function append_filter_fields(container_id) {
        var container = $(ST.dialogs.jquery_id(container_id)),
            form = container.find('form'),
            filter_fields = get_filter_fields(),
            filter_field_values = get_filter_field_values(filter_fields),
            input_field;
        $.each(filter_field_values, function(index, field) {
            input_field = $('<input type="hidden" />')
                .attr('name', field.name)
                .attr('value', field.value);
            form.append(input_field);
        });
    };
    function get_tick_format(count) {
        return function(d, i) {
            return Math.round(Math.abs(d*100/count));
        };
    };
    function get_ticks(max, count) {
        var delta = max/count;
        result = [];
        for (i=0; i<=count; i++) {
            result.push(i*delta);
            result.push(i*-delta);
        }
        return result;
    };
    return {
        get_filter_fields: get_filter_fields,
        get_filter_field_values: get_filter_field_values,
        on_section_report_sort: function(container_id, column_name,
                                         sort_on_name) {
            append_filter_fields(container_id);
            ST.table.on_form_sort(container_id, column_name, sort_on_name);
        },
        build_color_cell: function(container_id, score, colors) {
            var passing_colors = d3.interpolateRgb(
                    colors.passing.start,
                    colors.passing.end),
                not_passing_colors = d3.interpolateRgb(
                    colors.not_passing.start,
                    colors.not_passing.end);
                container = $(container_id);
            color = $('<span class="color">&nbsp;</span>');
            title = $('<span class="title">'+score.label+'</span>');
            if (score.is_passing) {
                colors = passing_colors;
            } else {
                colors = not_passing_colors;
            }
            color.css('backgroundColor', colors(score.color_weight));
            container.append(color, title);
        },
        build_chart: function(container_id, svg_size, container_size,
                              container_margins, skills_count,
                              passing_target_size, scores, colors) {
            var g = d3.select(container_id)
                    .append('svg')
                    .attr('width', svg_size.width)
                    .attr('height', svg_size.height)
                    .attr('class', 'chart')
                    .append('g')
                    .attr('transform',
                          'translate('+container_margins.left+',0)'),
                passing_colors = d3.interpolateRgb(
                    colors.passing.start,
                    colors.passing.end),
                not_passing_colors = d3.interpolateRgb(
                    colors.not_passing.start,
                    colors.not_passing.end),
                xTickCount = 5,
                xTickSize = 2,
                xTickPadding = 2,
                xTickValues,
                x,
                x_axis;
            if (skills_count == 0) {
                // XXX: no skills evaluated, review this approach
                skills_count = 1;
            }
            xTickValues = get_ticks(skills_count, xTickCount);
            x = d3.scale.linear()
                .domain([-skills_count, skills_count])
                .range([0, container_size.width]);
            x_axis = d3.svg.axis()
                .scale(x)
                .orient('top')
                .tickFormat(get_tick_format(skills_count))
                    .tickPadding(xTickPadding)
                .tickSize(xTickSize)
                .tickValues(xTickValues);
            g.append('g')
                .attr('class', 'bg-chart')
                .append('rect')
                .attr('width', container_size.width)
                .attr('height', container_size.height);
            g.append('g')
                .attr('class', 'bg-passing-target')
                .append('rect')
                .attr('width', passing_target_size.width)
                .attr('height', passing_target_size.height);
            g.selectAll('rect.score')
                .data(scores)
                .enter()
                .append('rect')
                .attr('class',
                      function(d, i) {
                          if (d.above_passing_target) {
                              return 'score above-passing-target';
                          }
                          return 'score';
                })
                .attr('x', function(d,i) {return x(Math.min(0, d.x));})
                .attr('y', 0)
                .attr('width', function(d,i) {return Math.abs(x(d.x)-x(0));})
                .attr('height', container_size.height-0.5)
                .attr('fill',
                      function(d, i) {
                          var colors;
                          if (d.is_passing) {
                              colors = passing_colors;
                          } else {
                              colors = not_passing_colors;
                          }
                          return colors(d.color_weight);
                })
                .append('title')
                .text(function(d, i) {return d.label + ': ' + d.percentage;});
            $('.above-passing-target').closest('tr')
                .addClass('above-passing-target');
            g.append('g')
                .attr('class', 'x-axis axis')
                .attr('transform',
                      'translate(0, '+(container_size.height-0.25)+')')
                .call(x_axis);
            g.append('g')
                .attr('class', 'y-axis axis')
                .append('line')
                .attr('x1', x(0))
                .attr('x2', x(0))
                .attr('y1', 0)
                .attr('y2', svg_size.height);
        }
    };
}();
