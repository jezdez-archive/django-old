var Actions = {
    init: function() {
        counterSpans = document.getElementsBySelector('span._acnt');
        counterContainer = document.getElementsBySelector('span.action-counter');
        allContainer = document.getElementsBySelector('div.actions span.all');
        actionContainer = document.getElementsBySelector('div.actions');
        actionCheckboxes = document.getElementsBySelector('tr input.action-select');
        acrossInputs = document.getElementsBySelector('div.actions input.select-across');
        acrossQuestions = document.getElementsBySelector('div.actions span.question');
        acrossClears = document.getElementsBySelector('div.actions span.clear');
        acrossQuestionLinks = document.getElementsBySelector('div.actions span.question a');
        acrossClearsLinks = document.getElementsBySelector('div.actions span.clear a');

        Actions.setDisplay(counterContainer, 'inline');
        selectAll = document.getElementById('action-toggle');
        if (selectAll) {
            Actions.setDisplay([selectAll], 'inline');
            addEvent(selectAll, 'click', function() {
                Actions.checker(selectAll.checked);
                Actions.counter();
            });
            for(var i = 0; i < acrossQuestionLinks.length; i++) {
                addEvent(acrossQuestionLinks[i], 'click', function() {
                    Actions.setAcrossInputs(1);
                    Actions.showClear()
                    return false;
                });
            }
            for(var i = 0; i < acrossClearsLinks.length; i++) {
                addEvent(acrossClearsLinks[i], 'click', function() {
                    selectAll.checked = false;
                    Actions.clearAcross();
                    Actions.checker(0);
                    Actions.counter();
                    return false;
                });
            }
        }
        lastChecked = null;
        for(var i = 0; i < actionCheckboxes.length; i++) {
            addEvent(actionCheckboxes[i], 'click', function(e) {
                if (!e) { var e = window.event; }
                var target = e.target ? e.target : e.srcElement;
                if (lastChecked && lastChecked != target && e.shiftKey == true) {
                    var inrange = false;
                    lastChecked.checked = target.checked;
                    Actions.toggleRow(lastChecked.parentNode.parentNode, target.checked);
                    for (var i = 0; i < actionCheckboxes.length; i++) {
                        if (actionCheckboxes[i] == lastChecked || actionCheckboxes[i] == target) {
                            inrange = (inrange) ? false : true;
                        }
                        if (inrange) {
                            actionCheckboxes[i].checked = target.checked;
                            Actions.toggleRow(actionCheckboxes[i].parentNode.parentNode, target.checked);
                        }
                    }
                }
                lastChecked = target;
                Actions.counter();
            });
        }
        var changelistTable = document.getElementsBySelector('#changelist table')[0];
        if (changelistTable) {
            addEvent(changelistTable, 'click', function(e) {
                if (!e) { var e = window.event; }
                var target = e.target ? e.target : e.srcElement;
                if (target.nodeType == 3) { target = target.parentNode; }
                if (target.className == 'action-select') {
                    var tr = target.parentNode.parentNode;
                    Actions.toggleRow(tr, target.checked);
                }
            });
        }
    },
    toggleRow: function(tr, checked) {
        if (checked && tr.className.indexOf('selected') == -1) {
            tr.className += ' selected';
        } else if (!checked) {
            tr.className = tr.className.replace(' selected', '');
        }  
    },
    setAcrossInputs: function(checked) {
        for(var i = 0; i < acrossInputs.length; i++) {
            acrossInputs[i].value = checked;
        }
    },
    checker: function(checked) {
        if (checked) {
            Actions.showQuestion()
        } else {
            Actions.reset();
        }
        for(var i = 0; i < actionCheckboxes.length; i++) {
            actionCheckboxes[i].checked = checked;
            Actions.toggleRow(actionCheckboxes[i].parentNode.parentNode, checked);
        }
    },
    setDisplay: function(elements, value) {
        for(var i = 0; i < elements.length; i++) {
            elements[i].style.display = value;
        }
    },
    showQuestion: function() {
        Actions.setDisplay(acrossQuestions, 'inline');
        Actions.setDisplay(acrossClears, 'none');
        Actions.setDisplay(allContainer, 'none');
    },
    showClear: function() {
        Actions.setDisplay(acrossQuestions, 'none');
        Actions.setDisplay(acrossClears, 'inline');
        Actions.setDisplay(counterContainer, 'none');
        Actions.setDisplay(allContainer, 'inline');
        for(var i = 0; i < actionContainer.length; i++) {
            Actions.toggleRow(actionContainer[i], true)
        }
    },
    reset: function() {
        Actions.setDisplay(allContainer, 'none')
        Actions.setDisplay(acrossQuestions, 'none');
        Actions.setDisplay(acrossClears, 'none');
        Actions.setDisplay(counterContainer, 'inline');
    },
    clearAcross: function() {
        Actions.reset()
        Actions.setAcrossInputs(0);
        for(var i = 0; i < actionContainer.length; i++) {
            Actions.toggleRow(actionContainer[i], false)
        }
    },
    counter: function() {
        counter = 0;
        for(var i = 0; i < actionCheckboxes.length; i++) {
            if(actionCheckboxes[i].checked){
                counter++;
            }
        }
        for(var i = 0; i < counterSpans.length; i++) {
            counterSpans[i].innerHTML = counter;
        }
        if (counter == actionCheckboxes.length) {
            selectAll.checked = true;
            Actions.showQuestion()
        } else {
            selectAll.checked = false;
            Actions.clearAcross()
        }
    }
};

addEvent(window, 'load', Actions.init);