(function($) {
    $.fn.djAdminInlines = function(prefix, options) {
        var settings = $.extend({
            odd: 'row1',
        }, options);
        var id_prefix = "#" + prefix;
        var total_forms = $(id_prefix + '-group input[id$="TOTAL_FORMS"]');
        var initial_forms = $(id_prefix + '-group').find('input[id$="INITIAL_FORMS"]');
        // since javascript is turned on, unhide the "add new <inline>" link
        $('.add_inline').show();
        // hide the extras, but only if there were no form errors
        if (!$('.errornote').html()) {
            if (parseInt(initial_forms.val()) > 0) {
                $(id_prefix + '-group .inline-item:gt(' + (initial_forms.val() - 1) + ')')
                    .not('.empty_form').remove();
            }
            else {
                $(id_prefix + '-group .inline-item').not('.empty_form').remove();
            }
            total_forms.val(parseInt(initial_forms.val()));
        }
        // 
        $(id_prefix + "-add").click(function() {
            var empty_id = id_prefix + '-empty';
            var total_value = total_forms.val().toString()
            total_forms.val(parseInt(total_forms.val())+1);
            $(empty_id)
                .clone(true)
                .insertBefore(empty_id)
                .html($(empty_id).html()
                                 .replace(/__prefix__/g, total_value))
                .attr('id', prefix + total_value)
                .removeClass()
                .find('.inline_label')
                    .html('#' + total_value)
                    .end()
                .parent()
                .find('tr:nth-child(odd)')
                    .addClass(settings.odd);
            return false;
        });
    return $(this);
    };
    /* Setup plugin defaults */
    $.fn.djAdminInlines.defaults = {
        prefix: 'form',                  // The form prefix for your django formset
        addText: 'add another',          // Text for the add link
        deleteText: 'remove',            // Text for the delete link
        addCssClass: 'add-row',          // CSS class applied to the add link
        deleteCssClass: 'delete-row',    // CSS class applied to the delete link
        formCssClass: 'dynamic-form',    // CSS class applied to each form in a formset
        added: null,                     // Function called each time a new form is added
        removed: null                    // Function called each time a form is deleted
    }
})(jQuery);