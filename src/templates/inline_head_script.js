var ns = {
    debug: {
        ERROR: true,
        WARNING: true,
        INFO: true,
        warn: function(msg) {
            if (this.WARNING) {
                console.warn(msg);
            }
        },
        info: function(msg) {
            if (this.INFO) {
                console.log(msg);
            }
        },
        error: function(msg) {
            if (this.ERROR) {
                console.error(msg);
            }
        }
    },
    django: {},
    menus: {
        openLoginForm : function() {
            document.getElementById('account-menu').style.display = 'block';
        },
        closeLoginForm : function() {
            document.getElementById('account-menu').style.display = 'none';
        },
        openSidebar : function() {
            document.getElementById("sidebar").classList.add("shown");
            let overlay = document.getElementById("overlay");
            if (overlay) {
                overlay.style.display = "block";
            }
        },
        closeSidebar : function() {
            document.getElementById("sidebar").classList.remove("shown");
            let overlay = document.getElementById("overlay");
            if (overlay) {
                overlay.style.display = "none";
            }
        }
    },
    theme: {},
};