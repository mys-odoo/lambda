odoo.define('pdf_preview.ReportPreview', function (require) {
    "use strict";
    
    var ActionManager = require('web.ActionManager');
    var core = require('web.core');
    var _t = core._t;
    ActionManager.include({
        _downloadReport: function (url) {
            var def = $.Deferred();
            console.log("Report!",url)
    
            if (!window.open(url)) {
                var message = _t('Enable popup windows!');
                this.do_warn(_t('Warning'), message, true);
                        }
    
            return def;
                },
        })
    });