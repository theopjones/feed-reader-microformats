// Copyright 2023 by Theodore Jones tjones2@fastmail.com 
//
// This code is licensed under the The Parity Public License 7.0.0
//
// As far as the law allows, this software comes as is, without any 
// warranty or condition, and the contributor won't be liable to anyone
// for any damages related to this software or this license, 
// under any kind of legal claim.


document.getElementById('get-api-key-button').addEventListener('click', function() {
    $.get("/api/create_new_api_key")
      .done(function(data) {
         console.log(data);
         var apiKey = data.api_key;
         var userId = data.user_id; // Extracting the user_id from the response
         document.getElementById('api-key-display').textContent = apiKey;
         document.getElementById('user-id-display').textContent = userId; // Displaying the user_id
      })
     .fail(function() {
        console.error("Error getting API key.");
        });
    });



    // Destroy API key  
    
    document.getElementById('destroy-api-button').addEventListener('click', function() {
    $.get("/api/destroy_all_api_key")
        .done(function(data) {
            alert("API keys have been removed.");
            window.location.href = "/login";
        })
        .fail(function() {
            alert("Error removing API Keys.");
        });
    });
    // Check if SMTP data is set
    $.get("/api/is_smtp_data_set")
        .done(function(data) {
            if(data.is_smtp_data_set) {
                // Fetch and fill the form with SMTP data
                $.get("/api/get_smtp_data")
                    .done(function(data) {
                        $('#host').val(data[0]);
                        $('#port').val(data[1]);
                        $('#username').val(data[2]);
                        $('#password').val(data[3]);
                    });
            }
        });

    // Submit form to set SMTP data
    $('#smtp-settings-form').on('submit', function(e) {
        e.preventDefault();

        $.ajax({
            url: "/api/set_needed_smtp_vars_into_db",
            type: "POST",
            data: {
                host: $('#host').val(),
                port: $('#port').val(),
                username: $('#username').val(),
                password: $('#password').val()
            },
            success: function(response) {
                $('#message').text(response.message);
            },
            error: function(response) {
                $('#message').text(response.error);
            }
        });
    });