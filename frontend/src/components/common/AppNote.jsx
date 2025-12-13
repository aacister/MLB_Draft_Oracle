import React from 'react';
import { FileText } from 'lucide-react';

const AppNoteComponent = () => {
    return ( 
        <div className="flex items-center space-x-3 bg-yellow-50 border border-yellow-200 mx-2 w-180  rounded-md px-3 py-2">
            <FileText className="w-5 h-5 text-yellow-600 flex-shrink-0" />
            <div className="text-xs text-yellow-800 font-medium">
                Due to cost and rate-limiting, MLB Draft Oracle is 
                configured to work with 2 teams, 4 rounds, and 4 player positions.
            </div>
        </div>
    );
};

export default AppNoteComponent;