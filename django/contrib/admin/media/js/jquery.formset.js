/**
 * jQuery Formset 1.1
 * @author Stanislaus Madueke (stan DOT madueke AT gmail DOT com)
 * @requires jQuery 1.2.6 or later
 *
 * Copyright (c) 2009, Stanislaus Madueke
 * All rights reserved.
 *
 * Licensed under the New BSD License
 * See: http://www.opensource.org/licenses/bsd-license.php
 */
(function($) {
    $.fn.formset = function(opts) {
        var options = $.extend({}, $.fn.formset.defaults, opts);

        var updateElementIndex = function(el, prefix, ndx) {
            var id_regex = new RegExp('(' + prefix + '-\\d+)');
            var replacement = prefix + '-' + ndx;
            if ($(el).attr("for")) $(el).attr("for", $(el).attr("for").replace(id_regex, replacement));
            if (el.id) el.id = el.id.replace(id_regex, replacement);
            if (el.name) el.name = el.name.replace(id_regex, replacement);
        };
        $(this).each(function(i) {
            $(this).addClass(options.formCssClass);
        });
        if ($(this).length) {
            var $addBtn;
            if ($(this).attr('tagName') == 'TR') {
                // If forms are laid out as table rows, insert the
                // "add" button in a new table row:
                var numCols = this.eq(0).children().length;
                $(this).parent().append('<tr class="' + options.addCssClass + '"><td colspan="' + numCols + '"><a href="javascript:void(0)">' + options.addText + '</a></tr>');
                $addBtn = $(this).parent().find('tr:last a');
            } else {
                // Otherwise, insert it immediately after the last form:
                $(this).filter(':last').after('<div class="' + options.addCssClass + '"><a href="javascript:void(0)">' + options.addText + '</a></div>');
                $addBtn = $(this).filter(':last').next();
            }
            $addBtn.click(function() {
                var nextIndex = parseInt($('#id_' + options.prefix + '-TOTAL_FORMS').val());
                var initialForms = parseInt($('#id_' + options.prefix + '-INITIAL_FORMS').val());
                var formCount = nextIndex + 1;
                var template = $('#' + options.prefix + '-empty');
                var row = template.clone(true).get(0);
                $(row).removeClass('empty_form').removeAttr('id').insertBefore($(template));
                $(row).html($(row).html().replace(/__prefix__/g, formCount));
                $(row).addClass(options.formCssClass).attr('id', options.prefix + formCount);

                // $(row).find('.inline_label').each(function() {
                //     var hash_regex = new RegExp('(#\\d+)');
                //     $(this).html($(this).html().replace(hash_regex, '#' + formCount));
                // });

                if ($(row).is('TR')) {
                    // If the forms are laid out in table rows, insert
                    // the remove button into the last table cell:
                    $(row).children(':last').append('<div class="' + options.deleteCssClass +'"><a href="javascript:void(0)">' + options.deleteText + '</a></div>');
                } else if ($(row).is('UL') || $(row).is('OL')) {
                    // If they're laid out as an ordered/unordered list,
                    // insert an <li> after the last list item:
                    $(row).append('<li class="' + options.deleteCssClass + '"><a href="javascript:void(0)">' + options.deleteText +'</a></li>');
                } else {
                    // Otherwise, just insert the remove button as the
                    // last child element of the form's container:
                    $(row).children(':first').append('<span class="' + options.deleteCssClass + '"><a href="javascript:void(0)">' + options.deleteText +'</a></span>');
                }
                // Update number of total forms
                $('#id_' + options.prefix + '-TOTAL_FORMS').val(formCount);
                $(row).find('.' + options.deleteCssClass + ' a').click(function() {
                    // Remove the parent form containing this button:
                    var row = $(this).parents('.' + options.formCssClass);
                    row.remove();
                    // If a post-delete callback was provided, call it with the deleted form:
                    if (options.removed) options.removed(row);
                    // Update the TOTAL_FORMS form count.
                    // Also, update names and ids for all remaining form controls
                    // so they remain in sequence:
                    var forms = $('.' + options.formCssClass);
                    $('#id_' + options.prefix + '-TOTAL_FORMS').val(forms.length);
                    // If there's only one form left, disable its delete button:
                    if (forms.length == 1) { $('a.' + options.deleteCssClass).hide(); }
                    for (var i=0, formCount=forms.length; i<formCount; i++) {
                        $(forms.get(i)).find('input,select,textarea,label').each(function() {
                            updateElementIndex(this, options.prefix, i);
                        });
                    }
                    return false;
                });
                $(row).find('input,select,textarea,label').each(function() {
                    updateElementIndex(this, options.prefix, nextIndex);
                    // If this is a checkbox or radiobutton, set uncheck it.
                    // Fix for Issue 1, reported by Wilson.Andrew.J:
                    var elem = $(this);
                    if (elem.is('input:checkbox') || elem.is('input:radio')) {
                        elem.attr('checked', false);
                    } else {
                        elem.val('');
                    }
                });
                // If a post-add callback was supplied, call it with the added form:
                if (options.added) options.added($(row));
                return false;
            });
        }
        return $(this);
    }

    /* Setup plugin defaults */
    $.fn.formset.defaults = {
        prefix: 'form',                  // The form prefix for your django formset
        addText: 'add another',          // Text for the add link
        deleteText: 'remove',            // Text for the delete link
        addCssClass: 'add-row',          // CSS class applied to the add link
        deleteCssClass: 'delete-row',    // CSS class applied to the delete link
        formCssClass: 'dynamic-form',    // CSS class applied to each form in a formset
        added: null,                     // Function called each time a new form is added
        removed: null                    // Function called each time a form is deleted
    }
})(jQuery)
