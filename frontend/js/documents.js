const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("pdf-file");
const categorySelect = document.getElementById("category");
const uploadButton = document.getElementById("upload-button");
const uploadStatus = document.getElementById("upload-status");
const documentsTable = document.getElementById("documents-table");

function showAlert(message, type = "success") {
    const container = document.getElementById("alert-container");
    container.replaceChildren();

    const alert = document.createElement("div");
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.setAttribute("role", "alert");
    alert.append(document.createTextNode(message));

    const closeButton = document.createElement("button");
    closeButton.type = "button";
    closeButton.className = "btn-close";
    closeButton.setAttribute("data-bs-dismiss", "alert");
    closeButton.setAttribute("aria-label", "Close");
    closeButton.addEventListener("click", () => alert.remove());

    alert.appendChild(closeButton);
    container.appendChild(alert);
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, options);

    if (!response.ok) {
        let message = `Request failed (${response.status})`;

        try {
            const body = await response.json();
            message = body.detail || message;
        } catch {
            // Keep the fallback message if the response is not JSON.
        }

        throw new Error(message);
    }

    return response.json();
}

async function loadCategories() {
    const data = await apiRequest("/api/categories");

    categorySelect.replaceChildren();

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select a category";
    categorySelect.appendChild(placeholder);

    data.categories.forEach((category) => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        categorySelect.appendChild(option);
    });
}

function addCell(row, value, className = "") {
    const cell = document.createElement("td");
    cell.textContent = value ?? "";

    if (className) {
        cell.className = className;
    }

    row.appendChild(cell);
    return cell;
}

function formatDate(value) {
    if (!value) return "—";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return "—";

    return date.toLocaleString();
}

async function loadDocuments() {
    documentsTable.replaceChildren();

    try {
        const data = await apiRequest("/api/documents");
        const documents = data.documents || [];

        let totalChunks = 0;
        const usedCategories = new Set();

        if (documents.length === 0) {
            const row = documentsTable.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 5;
            cell.className = "text-center text-muted py-4";
            cell.textContent = "No documents uploaded yet.";
        }

        documents.forEach((document) => {
            totalChunks += document.chunk_count || 0;
            usedCategories.add(document.category);

            const row = documentsTable.insertRow();

            addCell(row, document.filename, "filename-cell");
            addCell(row, document.category);
            addCell(row, document.chunk_count);
            addCell(row, formatDate(document.uploaded_at));

            const actionCell = row.insertCell();
            const deleteButton = documentButton();

            deleteButton.addEventListener("click", async () => {
                const confirmed = window.confirm(
                    `Delete "${document.filename}" and its stored embeddings?`
                );

                if (!confirmed) return;

                deleteButton.disabled = true;
                deleteButton.textContent = "Deleting...";

                try {
                    const result = await apiRequest(
                        `/api/documents/${encodeURIComponent(document.document_id)}`,
                        { method: "DELETE" }
                    );

                    showAlert(
                        `${result.message} Removed ${result.deleted_chunks} chunks.`
                    );

                    await loadDocuments();
                } catch (error) {
                    showAlert(error.message, "danger");
                    deleteButton.disabled = false;
                    deleteButton.textContent = "Delete";
                }
            });

            actionCell.appendChild(deleteButton);
        });

        document.getElementById("total-documents").textContent =
            documents.length;

        document.getElementById("total-chunks").textContent = totalChunks;

        document.getElementById("total-categories").textContent =
            usedCategories.size;
    } catch (error) {
        const row = documentsTable.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 5;
        cell.className = "text-danger";
        cell.textContent = `Could not load documents: ${error.message}`;
    }
}

function documentButton() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-outline-danger btn-sm";
    button.textContent = "Delete";
    return button;
}

uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = fileInput.files[0];
    const category = categorySelect.value;

    if (!file || !category) {
        showAlert("Select a PDF file and category.", "warning");
        return;
    }

    if (file.size > 25 * 1024 * 1024) {
        showAlert("The maximum upload size is 25 MB.", "warning");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);

    uploadButton.disabled = true;
    uploadStatus.textContent = "Processing PDF and creating embeddings...";

    try {
        const result = await apiRequest("/api/documents", {
            method: "POST",
            body: formData,
        });

        showAlert(
            `${result.filename} uploaded successfully. ` +
            `${result.stored_chunk_count} chunks stored.`
        );

        uploadForm.reset();
        await loadDocuments();
    } catch (error) {
        showAlert(error.message, "danger");
    } finally {
        uploadButton.disabled = false;
        uploadStatus.textContent = "";
    }
});

document.getElementById("refresh-button").addEventListener(
    "click",
    loadDocuments
);

async function initializeDashboard() {
    try {
        await loadCategories();
        await loadDocuments();
    } catch (error) {
        showAlert(error.message, "danger");
    }
}

initializeDashboard();