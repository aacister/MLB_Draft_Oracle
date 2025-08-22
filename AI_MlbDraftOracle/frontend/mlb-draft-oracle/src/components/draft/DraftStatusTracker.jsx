

const DraftStatusTracker = ({draftStatus}) => {

    return (
        <div className="p-1">
            <p className="text-blue-800 mt-1 text-xs animate-pulse">{ draftStatus}</p>
            {
            draftStatus.includes('Creating draft') && (
                <p className="text-blue-500 text-xs mt-0 italic">(This may take a few minutes)</p>
            )
            }
        </div>
    );
};
export default DraftStatusTracker;