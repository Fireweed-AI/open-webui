import { WEBUI_BASE_URL } from '$lib/constants';

let API_KEY = '';
let PROJECT_NUMBER = '';
let pickerApiLoaded = false;

async function getPickerConfig() {
	if (API_KEY && PROJECT_NUMBER) {
		return { apiKey: API_KEY, projectNumber: PROJECT_NUMBER };
	}

	const headers: Record<string, string> = {};
	if (typeof localStorage !== 'undefined' && localStorage.token) {
		headers.authorization = `Bearer ${localStorage.token}`;
	}

	const response = await fetch(`${WEBUI_BASE_URL}/api/config`, {
		headers
	});
	if (!response.ok) {
		throw new Error('Failed to fetch Google Drive configuration');
	}

	const config = await response.json();
	API_KEY = config.google_drive?.api_key;
	PROJECT_NUMBER = config.google_drive?.project_number;

	if (!API_KEY) {
		throw new Error('Google Drive API key not configured');
	}

	if (!PROJECT_NUMBER) {
		throw new Error('Google Drive project number not configured');
	}

	return { apiKey: API_KEY, projectNumber: PROJECT_NUMBER };
}

function loadPickerApi() {
	return new Promise((resolve, reject) => {
		if (typeof gapi === 'undefined') {
			const script = document.createElement('script');
			script.src = 'https://apis.google.com/js/api.js';
			script.onload = () => {
				gapi.load('picker', () => {
					pickerApiLoaded = true;
					resolve(true);
				});
			};
			script.onerror = reject;
			document.body.appendChild(script);
			return;
		}

		if (!pickerApiLoaded) {
			gapi.load('picker', () => {
				pickerApiLoaded = true;
				resolve(true);
			});
			return;
		}

		resolve(true);
	});
}

export const createGoogleDriveFolderPicker = async (accessToken: string) => {
	if (!accessToken) {
		throw new Error('Missing Google Drive access token');
	}

	const { apiKey, projectNumber } = await getPickerConfig();
	await loadPickerApi();

	return new Promise((resolve, reject) => {
		try {
			const view = new google.picker.DocsView(google.picker.ViewId.FOLDERS)
				.setIncludeFolders(true)
				.setSelectFolderEnabled(true);

			const picker = new google.picker.PickerBuilder()
				.enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
				.addView(view)
				.setOAuthToken(accessToken)
				.setAppId(projectNumber)
				.setDeveloperKey(apiKey)
				.setTitle('Select a folder')
				.setCallback((data: any) => {
					if (data[google.picker.Response.ACTION] === google.picker.Action.PICKED) {
						const folders = (data[google.picker.Response.DOCUMENTS] || []).map((doc: any) => ({
							id: doc[google.picker.Document.ID],
							name: doc[google.picker.Document.NAME]
						}));
						resolve(folders);
					} else if (data[google.picker.Response.ACTION] === google.picker.Action.CANCEL) {
						resolve(null);
					}
				})
				.build();

			picker.setVisible(true);
		} catch (error) {
			reject(error);
		}
	});
};
