// Copyright 2023 by Theodore Jones tjones2@fastmail.com 
//
// This code is licensed under the The Parity Public License 7.0.0
//
// As far as the law allows, this software comes as is, without any 
// warranty or condition, and the contributor won't be liable to anyone
// for any damages related to this software or this license, 
// under any kind of legal claim.


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
                window.location.href = "/login";
            }
        });
    }
});