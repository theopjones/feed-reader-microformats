// Written in 2023 by Theodore Jones tjones2@fastmail.com 
// To the extent possible under law, the author(s) have dedicated all copyright 
// and related and neighboring rights to this software to the public domain worldwide. 
// This software is distributed without any warranty. 
// http://creativecommons.org/publicdomain/zero/1.0/.


$.get("/api/is_smtp_data_set")
                .done(function(data) {
                    if(!data.is_smtp_data_set) {
                        // Show warning banner if SMTP settings are not set
                        $('#smtp-warning').show();
                    }
                });

$(document).ready(function(){
    // Check if the current page is not login page
    if (!window.location.href.includes("/login")) {
        $.get("/api/has_valid_api_key")
        .done(function(data, textStatus, xhr){
            if(xhr.status === 200){
                // Hide login link if user is logged in
                $('#main-nav li:nth-child(3)').hide();
            }
        })
        .fail(function(jqXHR, textStatus, errorThrown){
            if(jqXHR.status === 401){
                window.location.href = "{{ url_for('login_route') }}";
            }
        });
    }
});