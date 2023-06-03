// Written in 2023 by Theodore Jones tjones2@fastmail.com 
// To the extent possible under law, the author(s) have dedicated all copyright 
// and related and neighboring rights to this software to the public domain worldwide. 
// This software is distributed without any warranty. 
// http://creativecommons.org/publicdomain/zero/1.0/.

function downloadFeedArticles(feedUrl) {
    $.post("/api/download_articles_in_feed_and_update_last_updated", { feedurl: feedUrl })
        .done(function(data) {
            alert("Feed downloaded successfully.");
            getFeeds();
        })
        .fail(function() {
            alert("Error downloading feed articles.");
        });
}

function getFeeds() {
    $.get("/api/list_feeds_with_last_updated")
        .done(function(data) {
            var feedsHtml = "";
            for (var i = 0; i < data.length; i++) {
                var feed = data[i];
                feedsHtml += `<li>
                                ${feed[2]} - ${feed[0]} (last updated: ${feed[1]}) (probability: ${feed[3] || 'N/A'})
                                <button onclick="removeFeed('${feed[0]}')">Remove</button>
                                <button onclick="downloadFeedArticles('${feed[0]}')">Download Now</button>
                                <button onclick="updateFeedProbability('${feed[0]}')">Update Probability</button>
                            </li>`;
            }
            document.getElementById("feeds").innerHTML = "<ul>" + feedsHtml + "</ul>";
        })
        .fail(function() {
            console.log("Error getting feeds.")
        });
}

document.getElementById('feed-add-form').addEventListener('submit', function(event) {
    event.preventDefault();
    var name = document.getElementById('name').value;
    var url = document.getElementById('url').value;
    var probability = document.getElementById('probability').value;
    $.post("/api/add_feed", { name: name, feed: url, probability: probability })
        .done(function(data) {
            alert("Feed Added.");
            getFeeds();
        });
});

document.getElementById('feed-add-form-homepage').addEventListener('submit', function(event) {
    event.preventDefault();
    var name = document.getElementById('name-homepage').value;
    var url = document.getElementById('url-homepage').value;
    var probability = document.getElementById('probability-homepage').value;
    $.post("/api/get_rss_feed_url", { homepageurl: url })
        .done(function(data) {
            const from_server_rss_feed_json = data;
            $.post("/api/add_feed", { name: name, feed: from_server_rss_feed_json["rss_feed_url"], probability: probability })
                .done(function(data) {
                  alert("Feed Added.");
                  getFeeds();
                })
                .fail(function() {
                  alert("Error adding feed.");
                });
        })
        .fail(function() {
            alert("Error getting RSS feed URL.");
        });
});

function removeFeed(feed) {
    $.post("/api/remove_feed", { feed: feed })
        .done(function(data) {
            alert("Feed removed.");
            getFeeds();
        })
        .fail(function() {
            alert("Error removing feed.");
        });
}

function updateFeedProbability(feed) {
    var probability = prompt("Enter the new probability for the feed (0-1):");
    if (probability !== null) {
        $.post("/api/update_feed_probability", { feedurl: feed, probability: probability })
            .done(function(data) {
                alert("Feed probability updated.");
                getFeeds();
            })
            .fail(function() {
                alert("Error updating feed probability.");
            });
    }
}

getFeeds();

function refreshAllFeedsAndSendEmails() {
    $.get("/api/send_email_about_new_articles_in_all_feeds")
        .done(function(data) {
            alert(data.message);
            getFeeds();
        })
        .fail(function() {
            alert("Error refreshing feeds and sending emails.");
        });
}

document.getElementById('refresh-all-feeds').addEventListener('click', refreshAllFeedsAndSendEmails);

document.getElementById('delete-all-articles').addEventListener('click', function() {
    $.get("/api/destroy_all_articles_in_db")
        .done(function(data) {
            alert(data.message);
        })
        .fail(function() {
            alert("Error deleting all stored articles.");
        });
});
