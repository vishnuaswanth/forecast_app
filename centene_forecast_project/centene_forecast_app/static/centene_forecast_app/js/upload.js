

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
                if (response && response.message && response.message.toLowerCase().includes('file uploaded')) {
                    onUploadSuccess();
                } else if (response && response.success){
                    onUploadSuccess();
                } else {
                    console.log("not handled case in upload");
                    location.reload();
                }
                // If file_upload_id is returned, start polling for progress
                // var file_upload_id = response.file_upload_id;
                // if(file_upload_id){
                //     $('#progress-container').show();
                //     pollProgress(file_upload_id);

                // } else {
                //     // If not, simply reload the page (or handle error as needed)
                //     // location.reload();
                //     console.log("error occured")
                // }
            },
            error: function(xhr){
                // Handle error
                console.log("Error uploading file:", xhr.responseJSON.responseText) ;
                console.log(xhr);
                console.error("Error uploading file:", xhr)
                var errorMsg = xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : 'Error uploading file';
                $('#error-message').text(errorMsg).show();
                // $('#upload-btn').prop('disabled', false);
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
                error: function(){
                    clearInterval(interval);
                    alert('Error checking progress.');
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