import React from 'react';
const HistoryTab = ({draft_history}) => {
    console.log('Draft History:', draft_history);
    return (    
      <div>
        <h2 className="text-xl font-bold mb-4">
          Draft History ({draft_history?.length || 0} picks)
        </h2>
        <div className="bg-white rounded-lg shadow p-4 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Round.Pick
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Team
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Selection
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rationale
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {draft_history?.map((pick, index) => (
                  <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {pick.round}.{pick.pick}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {pick.team}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {pick.selection}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {pick.rationale}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(!draft_history || draft_history.length === 0) && (
            <div className="text-center py-8 text-gray-500">
              No picks made yet. Draft will begin shortly!
            </div>
          )}
        </div>
      </div>
    );
  };
  
  export default HistoryTab;