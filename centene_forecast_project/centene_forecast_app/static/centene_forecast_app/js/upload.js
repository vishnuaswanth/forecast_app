/**
 * Extract error message from XHR response.
 * Handles both responseJSON and responseText formats.
 * Combines 'error' and 'details' fields into a readable message.
 *
 * @param {Object} xhr - jQuery XHR object
 * @param {string} defaultMsg - Default message if extraction fails
 * @returns {string} Human-readable error message
 */
function getErrorMessage(xhr, defaultMsg) {
    defaultMsg = defaultMsg || 'An error occurred';

    // Try responseJSON first (jQuery auto-parses JSON responses)
    if (xhr.responseJSON && xhr.responseJSON.error) {
        var response = xhr.responseJSON.error;
        if (response.error) {
            var msg = response.error;
            if (response.details) {
                msg += ': ' + response.details;
            }
            return msg;
        }
    }


    // Fallback to parsing responseText
    if (xhr.responseText) {
        try {
            var parsed = JSON.parse(xhr.responseText);
            if (parsed.error) {
                var msg = parsed.error;
                if (parsed.details) {
                    msg += ': ' + parsed.details;
                }
                return msg;
            }
        } catch (e) {
            // Not valid JSON, return raw text if it looks like an error message
            if (xhr.responseText.length < 500) {
                return xhr.responseText;
            }
        }
    }

    return defaultMsg;
}

$(document).ready(function(){
    $('#uploadForm').on('submit', function(e){
        e.preventDefault();
        var formData = new FormData(this);
        disable_upload_button();
        $.ajax({
            url: fileUploadUrl,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response){
                console.log(response);
                // Check success field first (preferred), then fallback to message check
                if (response && response.success) {
                    onUploadSuccess();
                } else if (response && response.message && response.message.toLowerCase().includes('file uploaded')) {
                    onUploadSuccess();
                } else {
                    console.log("not handled case in upload");
                    location.reload();
                }
            },
            error: function(xhr){
                var errorMsg = getErrorMessage(xhr, 'Error uploading file');
                console.error("Error uploading file:", errorMsg);
                console.log(xhr);
                $('#error-message').text(errorMsg).show();
                enable_upload_button();
            }
        });
    });

    function enable_upload_button(){
        var button = $("#upload-btn");
        button.prop('disabled', false);
        button.html('<i class="fas fa-upload"></i> Upload');
    }

    function disable_upload_button(){
        var button = $("#upload-btn");
        button.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> uploading ...');
        button.prop('disabled', true);
    }


    function onUploadSuccess(){
        $('#error-message').text("").hide();
        $('#successMsg').show();
        $('#file_upload_input').val('');
        enable_upload_button();

        setTimeout(function() {
            $('#successMsg').hide();
        }, 10000); // 10 seconds

        // Refresh the table asynchronously
        setTimeout(function() {
            refreshTable();
        }, 0);

        Object.keys(sessionStorage)
            .filter(key => key.startsWith('dataview_dropdown_'))
            .forEach(key => sessionStorage.removeItem(key))
    }
    function pollProgress(file_upload_id){
        var interval = setInterval(function(){
            $.ajax({
                url: checkProgressUrl,
                data: { file_upload_id: file_upload_id },
                success: function(data){
                    $('#progress-bar').css('width', data.progress + '%').text(data.progress + '%');

                    if(data.status === 'completed' || data.status === 'error'){
                        clearInterval(interval);
                        $('#progress-container').hide();
                        $('#successMsg').show();

                        if(data.status === 'error'){
                            $('#error-message').show();
                            alert('Error processing file.');
                        } else {
                            refreshTable();
                        }
                    }
                },
                error: function(xhr){
                    clearInterval(interval);
                    var errorMsg = getErrorMessage(xhr, 'Error checking upload progress');
                    $('#error-message').text(errorMsg).show();
                }
            });
        }, 1000); // Poll every second
    }
});

function refreshTable(){
    $.ajax({
        url: refreshTableUrl,
        type: 'GET',
        success: function(response){
            // Extract the updated table container from the returned HTML
            var updatedTable = $(response).find('#table-container').html();
            $('#table-container').html(updatedTable);
        },
        error: function(xhr, status, error){
            console.error("Error refreshing table:", error);
        }
    });
}