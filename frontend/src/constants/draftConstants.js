export const API_BASE_URL = process.env.REACT_APP_API_URL;
//export const API_BASE_URL = 'http://localhost:8000';

export const POSITIONS = ['1B',  'C', 'OF', 'P'];

export const DRAFT_STATUS = {
  IN_PROGRESS: 'In Progress',
  COMPLETE: 'Complete'
};

export const TAB_CONFIG = [

  { id: 'history', label: 'Draft History', icon: 'History' },
  { id: 'teams', label: 'Team Rosters', icon: 'Users' },
  { id: 'draft', label: 'Draft Board', icon: 'List' }
];